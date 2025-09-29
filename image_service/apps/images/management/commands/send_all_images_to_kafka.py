import time
import json
import threading
import concurrent.futures
from queue import Queue
from collections import defaultdict
import ctypes
from django.core.management.base import BaseCommand
from django.db import connection
from messaging.producers import get_kafka_producer

class Command(BaseCommand):
    help = 'Send all images to Kafka for indexing in deck_search service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=16,
            help='Number of parallel Kafka producer workers (default: 16)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=200000,
            help='Number of images per database batch (default: 200000)'
        )
        parser.add_argument(
            '--queue-size',
            type=int,
            default=100000,
            help='Message queue buffer size (default: 100000)'
        )
        parser.add_argument(
            '--start-from',
            type=int,
            default=0,
            help='Start processing from this image ID'
        )
        parser.add_argument(
            '--max-images',
            type=int,
            default=None,
            help='Maximum number of images to process (for testing)'
        )
        parser.add_argument(
            '--log-interval',
            type=float,
            default=2.0,
            help='Progress logging interval in seconds (default: 2.0)'
        )

    def create_kafka_worker(self, worker_id, message_queue, stats, worker_stats, total_sent):
        """Worker function to send messages to Kafka"""
        producer = get_kafka_producer()
        if not producer:
            self.stdout.write(self.style.ERROR(f"Worker {worker_id}: Failed to create Kafka producer"))
            return

        sent_count = 0
        error_count = 0
        start_time = time.time()

        while True:
            try:
                message = message_queue.get(timeout=1)
                if message is None:  # Poison pill
                    break

                topic, data = message
                try:
                    producer.send(topic, value=data)
                    sent_count += 1

                    # Atomically increment total sent counter
                    with total_sent.get_lock():
                        total_sent.value += 1
                except Exception as send_error:
                    # Re-raise to be caught by outer exception handler
                    raise send_error

                # Update stats
                worker_stats[worker_id] = {
                    'sent': sent_count,
                    'errors': error_count,
                    'rate': sent_count / (time.time() - start_time) if time.time() > start_time else 0
                }

            except Exception as e:
                error_count += 1
                worker_stats[worker_id] = {
                    'sent': sent_count,
                    'errors': error_count,
                    'rate': sent_count / (time.time() - start_time) if time.time() > start_time else 0
                }
                if error_count % 10 == 0:  # Log errors every 10 for better debugging
                    self.stdout.write(self.style.ERROR(f"Worker {worker_id}: {error_count} errors, last error: {str(e)[:200]}..."))
                continue

        # Final flush
        producer.flush()
        final_time = time.time() - start_time
        final_rate = sent_count / final_time if final_time > 0 else 0

        stats[worker_id] = sent_count
        worker_stats[worker_id] = {
            'sent': sent_count,
            'errors': error_count,
            'rate': final_rate,
            'time': final_time
        }

        self.stdout.write(
            self.style.SUCCESS(
                f"Worker {worker_id}: Completed {sent_count} messages "
                f"({error_count} errors, {final_rate:.1f} msg/sec)"
            )
        )

    def progress_monitor(self, stats, worker_stats, total_images, start_time, log_interval, stop_event, total_sent, processed_count):
        """Real-time progress monitoring thread"""
        last_sent = 0
        last_time = start_time

        while not stop_event.is_set():
            time.sleep(log_interval)
            current_time = time.time()
            elapsed = current_time - start_time

            # Get thread-safe values
            current_sent = total_sent.value
            current_processed = processed_count.value

            # Calculate rates
            period_elapsed = current_time - last_time
            if period_elapsed > 0:
                current_rate = (current_sent - last_sent) / period_elapsed
                overall_rate = current_sent / elapsed if elapsed > 0 else 0
            else:
                current_rate = overall_rate = 0

            # Worker details
            worker_info = []
            for wid, ws in worker_stats.items():
                if isinstance(ws, dict) and ws.get('sent', 0) > 0:
                    worker_info.append(f"W{wid}:{ws['sent']}@{ws['rate']:.0f}")

            # Progress bar
            progress_percent = min(100, (current_sent / total_images) * 100) if total_images > 0 else 0
            progress_bar = "=" * int(progress_percent / 2) + ">" + " " * (50 - int(progress_percent / 2))

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{progress_bar}] {progress_percent:.1f}% | "
                    f"Sent: {current_sent:,}/{total_images:,} | "
                    f"Rate: {current_rate:.0f} current, {overall_rate:.0f} avg msg/sec | "
                    f"Queue: {0} | "  # TODO: Add queue size tracking
                    f"Elapsed: {elapsed:.1f}s | "
                    f"ETA: {(total_images - current_sent) / overall_rate:.0f}s" if overall_rate > 0 else "ETA: ∞"
                )
            )

            # Show worker details every 10 intervals
            if int(elapsed / log_interval) % 10 == 0 and worker_info:
                self.stdout.write(f"  Worker details: {' | '.join(worker_info[:8])}")

            last_sent = current_sent
            last_time = current_time

    def handle(self, *args, **options):
        workers = options['workers']
        batch_size = options['batch_size']
        queue_size = options['queue_size']
        start_from = options['start_from']
        max_images = options['max_images']
        log_interval = options['log_interval']

        start_time = time.time()

        # Get total count (respect max_images limit)
        with connection.cursor() as cursor:
            if max_images:
                cursor.execute("SELECT COUNT(*) FROM images_image WHERE id >= %s", [start_from])
                full_count = cursor.fetchone()[0]
                total_images = min(full_count, max_images)
            else:
                cursor.execute("SELECT COUNT(*) FROM images_image WHERE id >= %s", [start_from])
                total_images = cursor.fetchone()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f"🚀🚀🚀 HYPER-FAST BULK SEND STARTING 🚀🚀🚀"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"📊 Target: {total_images:,} images | Workers: {workers} | "
                f"Batch: {batch_size:,} | Queue: {queue_size:,}"
            )
        )

        # Create thread-safe shared variables
        total_sent = ctypes.c_longlong(0)
        processed_count = ctypes.c_longlong(0)

        # Create message queue and worker threads
        message_queue = Queue(maxsize=queue_size)
        stats = {}
        worker_stats = defaultdict(dict)

        # Progress monitoring
        stop_event = threading.Event()
        monitor_stats = {'processed': 0, 'sent': 0}

        # Start progress monitor thread
        monitor_thread = threading.Thread(
            target=self.progress_monitor,
            args=(stats, worker_stats, total_images, start_time, log_interval, stop_event, total_sent, processed_count)
        )
        monitor_thread.daemon = True
        monitor_thread.start()

        # Start worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            worker_futures = []
            for i in range(workers):
                stats[i] = 0
                future = executor.submit(self.create_kafka_worker, i, message_queue, stats, worker_stats, total_sent)
                worker_futures.append(future)

            # Stream data from database
            processed = 0
            batch_num = 1

            while processed < total_images:
                remaining = total_images - processed
                current_batch_size = min(batch_size, remaining)

                # Raw SQL query for maximum speed
                query = """
                SELECT
                    i.id, i.slug, i.title, i.description, i.image_url, i.release_year,
                    i.exclude_nudity, i.exclude_violence, i.created_at, i.updated_at,
                    m.slug as movie_slug, m.title as movie_title, m.year as movie_year,
                    mt.value as media_type,
                    c.value as color,
                    ar.value as aspect_ratio,
                    oformat.value as optical_format,
                    format.value as format,
                    ie.value as interior_exterior,
                    tod.value as time_of_day,
                    nop.value as number_of_people,
                    g.value as gender,
                    age.value as age,
                    eth.value as ethnicity,
                    fs.value as frame_size,
                    st.value as shot_type,
                    comp.value as composition,
                    ls.value as lens_size,
                    lt.value as lens_type,
                    l.value as lighting,
                    lt2.value as lighting_type,
                    ct.value as camera_type,
                    res.value as resolution,
                    fr.value as frame_rate
                FROM images_image i
                LEFT JOIN images_movie m ON i.movie_id = m.id
                LEFT JOIN images_mediatype mt ON i.media_type_id = mt.id
                LEFT JOIN images_color c ON i.color_id = c.id
                LEFT JOIN images_aspectratio ar ON i.aspect_ratio_id = ar.id
                LEFT JOIN images_opticalformat oformat ON i.optical_format_id = oformat.id
                LEFT JOIN images_format format ON i.format_id = format.id
                LEFT JOIN images_interiorexterior ie ON i.interior_exterior_id = ie.id
                LEFT JOIN images_timeofday tod ON i.time_of_day_id = tod.id
                LEFT JOIN images_numberofpeople nop ON i.number_of_people_id = nop.id
                LEFT JOIN images_gender g ON i.gender_id = g.id
                LEFT JOIN images_age age ON i.age_id = age.id
                LEFT JOIN images_ethnicity eth ON i.ethnicity_id = eth.id
                LEFT JOIN images_framesize fs ON i.frame_size_id = fs.id
                LEFT JOIN images_shottype st ON i.shot_type_id = st.id
                LEFT JOIN images_composition comp ON i.composition_id = comp.id
                LEFT JOIN images_lenssize ls ON i.lens_size_id = ls.id
                LEFT JOIN images_lenstype lt ON i.lens_type_id = lt.id
                LEFT JOIN images_lighting l ON i.lighting_id = l.id
                LEFT JOIN images_lightingtype lt2 ON i.lighting_type_id = lt2.id
                LEFT JOIN images_cameratype ct ON i.camera_type_id = ct.id
                LEFT JOIN images_resolution res ON i.resolution_id = res.id
                LEFT JOIN images_framerate fr ON i.frame_rate_id = fr.id
                WHERE i.id >= %s
                ORDER BY i.id
                LIMIT %s
                """

                with connection.cursor() as cursor:
                    cursor.execute(query, [start_from, current_batch_size])
                    rows = cursor.fetchall()

                    if not rows:
                        break

                    # Get column names
                    columns = [col[0] for col in cursor.description]

                    # Process batch
                    batch_messages = []
                    for row in rows:
                        row_dict = dict(zip(columns, row))

                        # Get related data (tags, genres)
                        image_id = row_dict['id']

                        # Get tags
                        cursor.execute("""
                            SELECT t.slug, t.name
                            FROM images_tag t
                            INNER JOIN images_image_tags it ON t.id = it.tag_id
                            WHERE it.image_id = %s
                        """, [image_id])
                        tags = [{'slug': row[0], 'name': row[1]} for row in cursor.fetchall()]

                        # Get genres
                        cursor.execute("""
                            SELECT g.value
                            FROM images_genre g
                            INNER JOIN images_image_genre ig ON g.id = ig.genre_id
                            WHERE ig.image_id = %s
                        """, [image_id])
                        genres = [row[0] for row in cursor.fetchall()]

                        # Build message
            data = {
                            "id": row_dict['id'],
                            "slug": row_dict['slug'],
                            "title": row_dict['title'],
                            "description": row_dict['description'],
                            "image_url": row_dict['image_url'],
                            "release_year": row_dict['release_year'],
                "movie": {
                                "slug": row_dict['movie_slug'],
                                "title": row_dict['movie_title'],
                                "year": row_dict['movie_year']
                            } if row_dict['movie_slug'] else None,
                            "tags": tags,
                            "genre": genres,
                            "media_type": row_dict['media_type'],
                            "color": row_dict['color'],
                            "aspect_ratio": row_dict['aspect_ratio'],
                            "optical_format": row_dict['optical_format'],
                            "format": row_dict['format'],
                            "interior_exterior": row_dict['interior_exterior'],
                            "time_of_day": row_dict['time_of_day'],
                            "number_of_people": row_dict['number_of_people'],
                            "gender": row_dict['gender'],
                            "age": row_dict['age'],
                            "ethnicity": row_dict['ethnicity'],
                            "frame_size": row_dict['frame_size'],
                            "shot_type": row_dict['shot_type'],
                            "composition": row_dict['composition'],
                            "lens_size": row_dict['lens_size'],
                            "lens_type": row_dict['lens_type'],
                            "lighting": row_dict['lighting'],
                            "lighting_type": row_dict['lighting_type'],
                            "camera_type": row_dict['camera_type'],
                            "resolution": row_dict['resolution'],
                            "frame_rate": row_dict['frame_rate'],
                            "exclude_nudity": row_dict['exclude_nudity'],
                            "exclude_violence": row_dict['exclude_violence'],
                            "created_at": row_dict['created_at'].isoformat() if row_dict['created_at'] else None,
                            "updated_at": row_dict['updated_at'].isoformat() if row_dict['updated_at'] else None
                        }

                    batch_messages.append(('image_created', data))

                    # Send batch to queue
                    for message in batch_messages:
                        message_queue.put(message)

                    # Update processed count atomically
                    processed += len(rows)
                    with processed_count.get_lock():
                        processed_count.value = processed
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0

                    # Calculate total messages sent by workers
                    total_sent = sum(stats.values())

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Batch {batch_num}: Processed {len(rows)} images "
                            f"(Total: {processed}/{total_images}, Queue: {message_queue.qsize()}, "
                            f"Workers sent: {total_sent}, Rate: {rate:.1f} img/sec)"
                        )
                    )
                    batch_num += 1

            # Send poison pills to stop workers
            for _ in range(workers):
                message_queue.put(None)

            # Wait for workers to finish
            concurrent.futures.wait(worker_futures)

        # Stop progress monitoring
        stop_event.set()
        monitor_thread.join(timeout=5)

        total_elapsed = time.time() - start_time
        final_rate = processed / total_elapsed if total_elapsed > 0 else 0
        total_sent = sum(stats.values())

        # Final statistics
        total_errors = sum(ws.get('errors', 0) for ws in worker_stats.values())
        avg_worker_rate = sum(ws.get('rate', 0) for ws in worker_stats.values()) / max(workers, 1)

        self.stdout.write("\n" + "="*80)
        self.stdout.write(
            self.style.SUCCESS(
                f"🎉🎉🎉 HYPER-FAST BULK SEND COMPLETED! 🎉🎉🎉"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"📈 Final Stats:"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Processed: {processed:,} images"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Sent: {total_sent:,} Kafka messages"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Errors: {total_errors:,}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Time: {total_elapsed:.1f} seconds"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Rate: {final_rate:.1f} img/sec ({final_rate * 3600:.0f} img/hour)"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Workers: {workers} (avg {avg_worker_rate:.1f} msg/sec each)"
            )
        )
        self.stdout.write("="*80)