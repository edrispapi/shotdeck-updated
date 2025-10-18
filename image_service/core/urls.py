# مسیر: image_service/core/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse, HttpResponse, Http404
import base64
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
from rest_framework.authtoken.views import obtain_auth_token
import os

def home_view(request):
    return JsonResponse({
        "service": "Image Service",
        "version": "1.0.0",
        "description": "مدیریت تصاویر و داده‌های بصری در پلتفرم Shotdeck",
        "stats": {
            "total_images": 1000,
            "indexed_images": 1310,
            "tags_count": 30,
            "movies_count": 20
        },
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "docs": "/api/schema/swagger-ui/",
            "images": "/api/images/",
            "token": "/api/api-token-auth/"
        },
        "status": "running",
        "timestamp": request.META.get('HTTP_HOST', 'localhost')
    })

def health_view(request):
    """Health check endpoint"""
    return JsonResponse({
        "status": "healthy",
        "service": "image_service",
        "timestamp": request.META.get('HTTP_HOST', 'localhost')
    })

def simple_schema_view(request):
    """Complete OpenAPI schema for Shotdeck Image Service with all database fields and no empty data"""
    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "Shotdeck Image Service API",
            "version": "2.0.0",
            "description": "Complete API for managing images, movies, and metadata with comprehensive filtering. All fields are validated to prevent empty/null data in requests."
        },
        "servers": [
            {"url": "http://localhost:51009", "description": "Development server"},
            {"url": "https://api.shotdeck.com", "description": "Production server"}
        ],
        "paths": {
            "/api/health/": {
                "get": {
                    "operationId": "health_check",
                    "summary": "Health Check",
                    "description": "Returns service health status with database connectivity and image count",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "healthy"},
                                            "database": {"type": "string", "example": "connected"},
                                            "image_count": {"type": "integer", "example": 10000},
                                            "timestamp": {"type": "string", "format": "date-time"}
                                        },
                                        "required": ["status", "database", "image_count", "timestamp"]
                                    }
                                }
                            }
                        },
                        "503": {
                            "description": "Service unavailable",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "unhealthy"},
                                            "error": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/images/": {
                "get": {
                    "operationId": "images_list",
                    "summary": "List Images",
                    "description": "Get paginated list of images with comprehensive filtering and search",
                    "tags": ["Images"],
                    "parameters": [
                        {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Search in title and description"},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}, "description": "Page number"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 200}, "description": "Items per page"},
                        {"name": "ordering", "in": "query", "schema": {"type": "string", "enum": ["-created_at", "-updated_at", "created_at", "title"]}, "description": "Sort order"},
                        {"name": "tags", "in": "query", "schema": {"type": "array", "items": {"type": "string"}}, "description": "Filter by tag names"},
                        {"name": "movie_slug", "in": "query", "schema": {"type": "string"}, "description": "Filter by movie slug"},
                        {"name": "release_year__gte", "in": "query", "schema": {"type": "integer"}, "description": "Minimum release year"},
                        {"name": "release_year__lte", "in": "query", "schema": {"type": "integer"}, "description": "Maximum release year"},
                        {"name": "media_type", "in": "query", "schema": {"type": "string"}, "description": "Filter by media type"},
                        {"name": "color", "in": "query", "schema": {"type": "string"}, "description": "Filter by color"},
                        {"name": "shot_type", "in": "query", "schema": {"type": "string"}, "description": "Filter by shot type"},
                        {"name": "lighting", "in": "query", "schema": {"type": "string"}, "description": "Filter by lighting"},
                        {"name": "time_of_day", "in": "query", "schema": {"type": "string"}, "description": "Filter by time of day"},
                        {"name": "interior_exterior", "in": "query", "schema": {"type": "string"}, "description": "Filter by interior/exterior"},
                        {"name": "gender", "in": "query", "schema": {"type": "string"}, "description": "Filter by gender"},
                        {"name": "age", "in": "query", "schema": {"type": "string"}, "description": "Filter by age group"},
                        {"name": "ethnicity", "in": "query", "schema": {"type": "string"}, "description": "Filter by ethnicity"}
                    ],
                    "responses": {
                        "200": {
                            "description": "List of images",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean", "example": True},
                                            "count": {"type": "integer", "example": 1250},
                                            "results": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/Image"}
                                            },
                                            "filters_applied": {"type": "object"},
                                            "message": {"type": "string"},
                                            "source": {"type": "string"}
                                        },
                                        "required": ["success", "count", "results"]
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/image/{slug}/": {
                "get": {
                    "operationId": "image_detail",
                    "summary": "Get Image Detail",
                    "description": "Get detailed information for a specific image",
                    "tags": ["Images"],
                    "parameters": [
                        {"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Image slug"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Image details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Image"}
                                }
                            }
                        },
                        "404": {"description": "Image not found"}
                    }
                }
            },
            "/api/movies/": {
                "get": {
                    "operationId": "movies_list",
                    "summary": "List Movies",
                    "description": "Get paginated list of movies with comprehensive filtering and search",
                    "tags": ["Movies"],
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}, "description": "Page number"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 200}, "description": "Items per page"},
                        {"name": "ordering", "in": "query", "schema": {"type": "string", "enum": ["-year", "year", "title", "-title"]}, "description": "Sort order"},
                        {"name": "title", "in": "query", "schema": {"type": "string"}, "description": "Search in movie title (case-insensitive)"},
                        {"name": "year", "in": "query", "schema": {"type": "integer"}, "description": "Filter by exact year"},
                        {"name": "year__gte", "in": "query", "schema": {"type": "integer"}, "description": "Minimum release year"},
                        {"name": "year__lte", "in": "query", "schema": {"type": "integer"}, "description": "Maximum release year"},
                        {"name": "genre", "in": "query", "schema": {"type": "string"}, "description": "Search in movie genre (case-insensitive)"},
                        {"name": "director", "in": "query", "schema": {"type": "string"}, "description": "Search in director name (case-insensitive)"},
                        {"name": "cinematographer", "in": "query", "schema": {"type": "string"}, "description": "Search in cinematographer name (case-insensitive)"},
                        {"name": "country", "in": "query", "schema": {"type": "string"}, "description": "Search in country (case-insensitive)"},
                        {"name": "language", "in": "query", "schema": {"type": "string"}, "description": "Search in language (case-insensitive)"}
                    ],
                    "responses": {
                        "200": {
                            "description": "List of movies",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "count": {"type": "integer"},
                                            "next": {"type": "string", "nullable": True},
                                            "previous": {"type": "string", "nullable": True},
                                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/Movie"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/movie/{slug}/": {
                "get": {
                    "operationId": "movie_detail",
                    "summary": "Get Movie Detail",
                    "description": "Get detailed information for a specific movie",
                    "tags": ["Movies"],
                    "parameters": [
                        {"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Movie slug"}
                    ],
                    "responses": {
                        "200": {"description": "Movie details", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Movie"}}}},
                        "404": {"description": "Movie not found"}
                    }
                }
            },
            "/api/tags/{slug}/": {
                "get": {
                    "operationId": "tag_detail",
                    "summary": "Get Tag Detail",
                    "description": "Get detailed information for a specific tag including usage statistics",
                    "tags": ["Tags"],
                    "parameters": [
                        {"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Tag slug"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Tag details with statistics",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TagDetail"}
                                }
                            }
                        },
                        "404": {"description": "Tag not found"}
                    }
                }
            },
            "/api/images/filters/": {
                "get": {
                    "operationId": "image_filters",
                    "summary": "Get Available Filters / Filter Images",
                    "description": "Get all available filter options for image search when no parameters provided, or filter images when search parameters are included",
                    "tags": ["Filters"],
                    "parameters": [
                        {"name": "search", "in": "query", "schema": {"type": "string"}, "description": "Search in titles and descriptions (text input)"},
                        {"name": "tags", "in": "query", "schema": {"type": "string"}, "description": "Filter by tag names (comma-separated, text input)"},
                        {"name": "movie", "in": "query", "schema": {"type": "string"}, "description": "Filter by movie (dropdown - see /api/images/filters/ for options)"},
                        {"name": "actor", "in": "query", "schema": {"type": "string"}, "description": "Filter by actor (dropdown - see /api/images/filters/ for options)"},
                        {"name": "camera", "in": "query", "schema": {"type": "string"}, "description": "Filter by camera (dropdown - see /api/images/filters/ for options)"},
                        {"name": "lens", "in": "query", "schema": {"type": "string"}, "description": "Filter by lens (dropdown - see /api/images/filters/ for options)"},
                        {"name": "location", "in": "query", "schema": {"type": "string"}, "description": "Filter by location (dropdown - see /api/images/filters/ for options)"},
                        {"name": "setting", "in": "query", "schema": {"type": "string"}, "description": "Filter by setting (dropdown - see /api/images/filters/ for options)"},
                        {"name": "film_stock", "in": "query", "schema": {"type": "string"}, "description": "Filter by film stock (dropdown - see /api/images/filters/ for options)"},
                        {"name": "shot_time", "in": "query", "schema": {"type": "string"}, "description": "Filter by shot time (dropdown - see /api/images/filters/ for options)"},
                        {"name": "description", "in": "query", "schema": {"type": "string"}, "description": "Filter by description (text input)"},
                        {"name": "vfx_backing", "in": "query", "schema": {"type": "string"}, "description": "Filter by VFX backing (dropdown - see /api/images/filters/ for options)"},
                        {"name": "media_type", "in": "query", "schema": {"type": "string", "enum": ["Motion Picture", "Broadcast", "Commercial", "Documentary", "Still"]}, "description": "Filter by media type (dropdown selection)"},
                        {"name": "genre", "in": "query", "schema": {"type": "string", "enum": ["Drama", "Comedy", "Action", "Crime", "Thriller", "Horror", "Romance", "Adventure"]}, "description": "Filter by genre (dropdown selection)"},
                        {"name": "time_period", "in": "query", "schema": {"type": "string"}, "description": "Filter by time period (dropdown - see /api/images/filters/ for options)"},
                        {"name": "color", "in": "query", "schema": {"type": "string", "enum": ["Warm", "Desaturated", "White", "Cool", "Bright"]}, "description": "Filter by color (dropdown selection)"},
                        {"name": "shade", "in": "query", "schema": {"type": "string"}, "description": "Filter by color shade (HEX_COLOR~DISTANCE~PROPORTION, text input)"},
                        {"name": "aspect_ratio", "in": "query", "schema": {"type": "string", "enum": ["16:9", "4:3", "2.35:1", "1.85:1", "1:1"]}, "description": "Filter by aspect ratio (dropdown selection)"},
                        {"name": "optical_format", "in": "query", "schema": {"type": "string", "enum": ["Spherical", "Anamorphic", "Super 35", "VistaVision"]}, "description": "Filter by optical format (dropdown selection)"},
                        {"name": "lab_process", "in": "query", "schema": {"type": "string"}, "description": "Filter by lab process (dropdown - see /api/images/filters/ for options)"},
                        {"name": "format", "in": "query", "schema": {"type": "string", "enum": ["35mm", "16mm", "Super 16mm", "65mm", "70mm", "8mm"]}, "description": "Filter by film format (dropdown selection)"},
                        {"name": "interior_exterior", "in": "query", "schema": {"type": "string", "enum": ["Interior", "Exterior", "Mixed"]}, "description": "Filter by interior/exterior (dropdown selection)"},
                        {"name": "time_of_day", "in": "query", "schema": {"type": "string", "enum": ["Dawn", "Morning", "Noon", "Afternoon", "Evening", "Dusk", "Night"]}, "description": "Filter by time of day (dropdown selection)"},
                        {"name": "number_of_people", "in": "query", "schema": {"type": "string", "enum": ["1", "2", "3-5", "6-10", "11-20", "21-50", "50+"]}, "description": "Filter by number of people (dropdown selection)"},
                        {"name": "gender", "in": "query", "schema": {"type": "string", "enum": ["Male", "Female", "Mixed", "Unspecified"]}, "description": "Filter by gender (dropdown selection)"},
                        {"name": "age", "in": "query", "schema": {"type": "string", "enum": ["Child", "Teen", "Young Adult", "Adult", "Middle-aged", "Senior"]}, "description": "Filter by age (dropdown selection)"},
                        {"name": "ethnicity", "in": "query", "schema": {"type": "string", "enum": ["Caucasian", "African", "Asian", "Hispanic", "Middle Eastern", "Mixed"]}, "description": "Filter by ethnicity (dropdown selection)"},
                        {"name": "frame_size", "in": "query", "schema": {"type": "string", "enum": ["Full Frame", "APS-C", "APS-H", "Medium Format", "Large Format"]}, "description": "Filter by frame size (dropdown selection)"},
                        {"name": "shot_type", "in": "query", "schema": {"type": "string", "enum": ["Wide Shot", "Close-up", "Medium Shot", "Extreme Close-up", "Long Shot", "Overhead"]}, "description": "Filter by shot type (dropdown selection)"},
                        {"name": "composition", "in": "query", "schema": {"type": "string", "enum": ["Rule of Thirds", "Centered", "Leading Lines", "Symmetrical", "Asymmetrical"]}, "description": "Filter by composition (dropdown selection)"},
                        {"name": "lens_type", "in": "query", "schema": {"type": "string", "enum": ["Prime", "Zoom", "Wide Angle", "Telephoto", "Macro"]}, "description": "Filter by lens type (dropdown selection)"},
                        {"name": "lighting", "in": "query", "schema": {"type": "string", "enum": ["Natural", "Artificial", "Mixed", "Studio", "Practical"]}, "description": "Filter by lighting (dropdown selection)"},
                        {"name": "lighting_type", "in": "query", "schema": {"type": "string", "enum": ["Tungsten", "HMI", "LED", "Fluorescent", "Natural + Artificial"]}, "description": "Filter by lighting type (dropdown selection)"},
                        {"name": "director", "in": "query", "schema": {"type": "string"}, "description": "Filter by director (dropdown - see /api/images/filters/ for options)"},
                        {"name": "cinematographer", "in": "query", "schema": {"type": "string"}, "description": "Filter by cinematographer (dropdown - see /api/images/filters/ for options)"},
                        {"name": "editor", "in": "query", "schema": {"type": "string"}, "description": "Filter by editor (dropdown - see /api/images/filters/ for options)"},
                        {"name": "costume_designer", "in": "query", "schema": {"type": "string"}, "description": "Filter by costume designer (dropdown - see /api/images/filters/ for options)"},
                        {"name": "production_designer", "in": "query", "schema": {"type": "string"}, "description": "Filter by production designer (dropdown - see /api/images/filters/ for options)"},
                        {"name": "colorist", "in": "query", "schema": {"type": "string"}, "description": "Filter by colorist (dropdown - see /api/images/filters/ for options)"},
                        {"name": "artist", "in": "query", "schema": {"type": "string"}, "description": "Filter by artist (dropdown - see /api/images/filters/ for options)"},
                        {"name": "filming_location", "in": "query", "schema": {"type": "string"}, "description": "Filter by filming location (dropdown - see /api/images/filters/ for options)"},
                        {"name": "location_type", "in": "query", "schema": {"type": "string", "enum": ["Studio", "Location", "Green Screen", "Sound Stage", "Exterior Only"]}, "description": "Filter by location type (dropdown selection)"},
                        {"name": "year", "in": "query", "schema": {"type": "string"}, "description": "Filter by year (dropdown - see /api/images/filters/ for options)"},
                        {"name": "frame_rate", "in": "query", "schema": {"type": "string", "enum": ["23.98 fps", "24 fps", "25 fps", "29.97 fps", "30 fps", "50 fps", "59.94 fps", "60 fps"]}, "description": "Filter by frame rate (dropdown selection)"},
                        {"name": "lab_process", "in": "query", "schema": {"type": "string"}, "description": "Filter by lab process (dropdown - see /api/images/filters/ for options)"},
                        {"name": "lens_size", "in": "query", "schema": {"type": "string", "enum": ["Wide Angle (10-24mm)", "Standard (24-70mm)", "Medium Telephoto (70-135mm)", "Telephoto (135mm+)", "Macro"]}, "description": "Filter by lens size (dropdown selection)"},
                        {"name": "resolution", "in": "query", "schema": {"type": "string", "enum": ["HD (1920x1080)", "4K (3840x2160)", "8K (7680x4320)", "2K (2048x1080)", "SD (720x480)"]}, "description": "Filter by resolution (dropdown selection)"},
                        {"name": "shot_time", "in": "query", "schema": {"type": "string"}, "description": "Filter by shot time (dropdown - see /api/images/filters/ for options)"},
                        {"name": "description_filter", "in": "query", "schema": {"type": "string"}, "description": "Filter by description (dropdown - see /api/images/filters/ for options)"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 200}, "description": "Number of results per page"},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0}, "description": "Pagination offset"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Filter configuration with options (when no parameters) or filtered image results (when parameters provided)",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "oneOf": [
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "success": {"type": "boolean"},
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "filters": {"type": "array", "items": {"type": "object"}},
                                                            "working_filters": {"type": "array", "items": {"type": "string"}},
                                                            "empty_filters": {"type": "array", "items": {"type": "string"}},
                                                            "working_filters_count": {"type": "integer"},
                                                            "empty_filters_count": {"type": "integer"}
                                                        }
                                                    },
                                                    "smart_filtering": {"type": "object"}
                                                },
                                                "description": "Filter configuration returned when no search parameters provided"
                                            },
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "success": {"type": "boolean"},
                                                    "count": {"type": "integer"},
                                                    "results": {"type": "array", "items": {"$ref": "#/components/schemas/Image"}},
                                                    "total": {"type": "integer"},
                                                    "filters_applied": {"type": "object"},
                                                    "smart_filtering": {"type": "object"},
                                                    "message": {"type": "string"},
                                                    "source": {"type": "string"}
                                                },
                                                "description": "Filtered image results returned when search parameters provided"
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Image": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "slug": {"type": "string", "readOnly": True},
                        "title": {"type": "string", "minLength": 1, "maxLength": 255},
                        "description": {"type": "string", "default": ""},
                        "image_url": {"type": "string", "format": "uri", "minLength": 1},
                        "tags": {"type": "array", "items": {"$ref": "#/components/schemas/Tag"}},
                        "release_year": {"type": "integer", "nullable": True},
                        "movie": {"type": "integer", "nullable": True},
                        "movie_value": {"type": "string", "readOnly": True},
                        "movie_slug": {"type": "string", "readOnly": True},
                        "media_type": {"type": "integer", "nullable": True},
                        "media_type_value": {"type": "string", "readOnly": True},
                        "genre": {"type": "array", "items": {"type": "integer"}},
                        "genre_value": {"type": "string", "readOnly": True},
                        "color": {"type": "integer", "nullable": True},
                        "color_value": {"type": "string", "readOnly": True},
                        "dominant_colors": {"type": "array", "nullable": True},
                        "primary_color_hex": {"type": "string", "nullable": True},
                        "primary_colors": {"type": "array", "nullable": True},
                        "secondary_color_hex": {"type": "string", "nullable": True},
                        "color_palette": {"type": "array", "nullable": True},
                        "color_samples": {"type": "array", "nullable": True},
                        "color_histogram": {"type": "object", "nullable": True},
                        "color_search_terms": {"type": "array", "nullable": True},
                        "color_temperature": {"type": "string", "nullable": True},
                        "hue_range": {"type": "string", "nullable": True},
                        "aspect_ratio": {"type": "integer", "nullable": True},
                        "aspect_ratio_value": {"type": "string", "readOnly": True},
                        "optical_format": {"type": "integer", "nullable": True},
                        "optical_format_value": {"type": "string", "readOnly": True},
                        "format": {"type": "integer", "nullable": True},
                        "format_value": {"type": "string", "readOnly": True},
                        "interior_exterior": {"type": "integer", "nullable": True},
                        "interior_exterior_value": {"type": "string", "readOnly": True},
                        "time_of_day": {"type": "integer", "nullable": True},
                        "time_of_day_value": {"type": "string", "readOnly": True},
                        "number_of_people": {"type": "integer", "nullable": True},
                        "number_of_people_value": {"type": "string", "readOnly": True},
                        "gender": {"type": "integer", "nullable": True},
                        "gender_value": {"type": "string", "readOnly": True},
                        "age": {"type": "integer", "nullable": True},
                        "age_value": {"type": "string", "readOnly": True},
                        "ethnicity": {"type": "integer", "nullable": True},
                        "ethnicity_value": {"type": "string", "readOnly": True},
                        "frame_size": {"type": "integer", "nullable": True},
                        "frame_size_value": {"type": "string", "readOnly": True},
                        "shot_type": {"type": "integer", "nullable": True},
                        "shot_type_value": {"type": "string", "readOnly": True},
                        "composition": {"type": "integer", "nullable": True},
                        "composition_value": {"type": "string", "readOnly": True},
                        "lens_size": {"type": "integer", "nullable": True},
                        "lens_size_value": {"type": "string", "readOnly": True},
                        "lens_type": {"type": "integer", "nullable": True},
                        "lens_type_value": {"type": "string", "readOnly": True},
                        "lighting": {"type": "integer", "nullable": True},
                        "lighting_value": {"type": "string", "readOnly": True},
                        "lighting_type": {"type": "integer", "nullable": True},
                        "lighting_type_value": {"type": "string", "readOnly": True},
                        "camera_type": {"type": "integer", "nullable": True},
                        "camera_type_value": {"type": "string", "readOnly": True},
                        "resolution": {"type": "integer", "nullable": True},
                        "resolution_value": {"type": "string", "readOnly": True},
                        "frame_rate": {"type": "integer", "nullable": True},
                        "frame_rate_value": {"type": "string", "readOnly": True},
                        "time_period": {"type": "integer", "nullable": True},
                        "time_period_value": {"type": "string", "readOnly": True},
                        "lab_process": {"type": "integer", "nullable": True},
                        "lab_process_value": {"type": "string", "readOnly": True},
                        "director": {"type": "integer", "nullable": True},
                        "director_value": {"type": "string", "readOnly": True},
                        "cinematographer": {"type": "integer", "nullable": True},
                        "cinematographer_value": {"type": "string", "readOnly": True},
                        "editor": {"type": "integer", "nullable": True},
                        "editor_value": {"type": "string", "readOnly": True},
                        "colorist": {"type": "string", "default": ""},
                        "costume_designer": {"type": "string", "default": ""},
                        "production_designer": {"type": "string", "default": ""},
                        "actor": {"type": "integer", "nullable": True},
                        "actor_value": {"type": "string", "readOnly": True},
                        "camera": {"type": "integer", "nullable": True},
                        "camera_value": {"type": "string", "readOnly": True},
                        "lens": {"type": "integer", "nullable": True},
                        "lens_value": {"type": "string", "readOnly": True},
                        "location": {"type": "integer", "nullable": True},
                        "location_value": {"type": "string", "readOnly": True},
                        "setting": {"type": "integer", "nullable": True},
                        "setting_value": {"type": "string", "readOnly": True},
                        "film_stock": {"type": "integer", "nullable": True},
                        "film_stock_value": {"type": "string", "readOnly": True},
                        "shot_time": {"type": "integer", "nullable": True},
                        "shot_time_value": {"type": "string", "readOnly": True},
                        "description_filter": {"type": "integer", "nullable": True},
                        "description_filter_value": {"type": "string", "readOnly": True},
                        "vfx_backing": {"type": "integer", "nullable": True},
                        "vfx_backing_value": {"type": "string", "readOnly": True},
                        "shade": {"type": "integer", "nullable": True},
                        "shade_value": {"type": "string", "readOnly": True},
                        "artist": {"type": "integer", "nullable": True},
                        "artist_value": {"type": "string", "readOnly": True},
                        "filming_location": {"type": "integer", "nullable": True},
                        "filming_location_value": {"type": "string", "readOnly": True},
                        "location_type": {"type": "integer", "nullable": True},
                        "location_type_value": {"type": "string", "readOnly": True},
                        "exclude_nudity": {"type": "boolean", "default": False},
                        "exclude_violence": {"type": "boolean", "default": False},
                        "created_at": {"type": "string", "format": "date-time", "readOnly": True},
                        "updated_at": {"type": "string", "format": "date-time", "readOnly": True}
                    },
                    "required": ["title", "image_url"]
                },
                "Movie": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "slug": {"type": "string", "readOnly": True},
                        "title": {"type": "string", "minLength": 1, "maxLength": 255},
                        "description": {"type": "string", "default": ""},
                        "year": {"type": "integer", "nullable": True},
                        "genre": {"type": "string", "default": ""},
                        "director": {"type": "integer", "nullable": True},
                        "director_value": {"type": "string", "readOnly": True},
                        "director_slug": {"type": "string", "readOnly": True},
                        "cinematographer": {"type": "integer", "nullable": True},
                        "cinematographer_value": {"type": "string", "readOnly": True},
                        "cinematographer_slug": {"type": "string", "readOnly": True},
                        "editor": {"type": "integer", "nullable": True},
                        "editor_value": {"type": "string", "readOnly": True},
                        "editor_slug": {"type": "string", "readOnly": True},
                        "colorist": {"type": "string", "default": ""},
                        "costume_designer": {"type": "string", "default": ""},
                        "production_designer": {"type": "string", "default": ""},
                        "cast": {"type": "string", "default": ""},
                        "duration": {"type": "integer", "nullable": True},
                        "country": {"type": "string", "default": ""},
                        "language": {"type": "string", "default": ""},
                        "image_count": {"type": "integer", "readOnly": True}
                    },
                    "required": ["title"]
                },
                "MovieImage": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "slug": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "movie_title": {"type": "string"},
                        "movie_slug": {"type": "string"},
                        "color_value": {"type": "string"},
                        "media_type_value": {"type": "string"},
                        "tags_count": {"type": "integer"},
                        "genre_count": {"type": "integer"},
                        "release_year": {"type": "integer", "nullable": True},
                        "dominant_colors": {"type": "array"},
                        "primary_color_hex": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"}
                    }
                },
                "Tag": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "slug": {"type": "string", "readOnly": True},
                        "name": {"type": "string", "minLength": 1, "maxLength": 200}
                    },
                    "required": ["name"]
                },
                "TagDetail": {
                    "type": "object",
                    "allOf": [{"$ref": "#/components/schemas/Tag"}],
                    "properties": {
                        "usage_count": {"type": "integer"},
                        "movies": {"type": "array", "items": {"type": "object"}},
                        "recent_images": {"type": "array", "items": {"$ref": "#/components/schemas/Image"}}
                    }
                }
            },
            "securitySchemes": {
                "tokenAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "Token-based authentication with format: Token <your-token>"
                }
            }
        },
        "security": [{"tokenAuth": []}],
        "tags": [
            {"name": "Health", "description": "Health check endpoints"},
            {"name": "Images", "description": "Image management and search"},
            {"name": "Movies", "description": "Movie management"},
            {"name": "Tags", "description": "Tag management"},
            {"name": "Filters", "description": "Filter options and configuration"}
        ]
    }
    return JsonResponse(schema)

def custom_swagger_ui_view(request):
    """Custom Swagger UI view that doesn't use drf_spectacular"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Shotdeck Image Service API</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui.css" />
    <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5.10.3/favicon-32x32.png" sizes="32x32" />
    <style>
        html { box-sizing: border-box; overflow-y: scroll; }
        *, *:after, *:before { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-standalone-preset.js"></script>
    <script>
        const ui = SwaggerUIBundle({
            url: '/api/schema/?format=json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout",
            validatorUrl: null,
            tryItOutEnabled: true,
            displayRequestDuration: true,
            docExpansion: 'list',
            filter: true,
            persistAuthorization: true
        });
    </script>
</body>
</html>
    """
    return HttpResponse(html_content, content_type='text/html')

def test_schema_view(request):
    """Test view to verify schema loading works"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Schema Loading</title>
</head>
<body>
    <h1>Testing Schema Load</h1>
    <div id="result"></div>

    <script>
        fetch('/api/schema/?format=json')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                document.getElementById('result').innerHTML =
                    '<h2 style="color: green;">SUCCESS!</h2>' +
                    '<p>OpenAPI version: ' + data.openapi + '</p>' +
                    '<p>Title: ' + data.info.title + '</p>';
            })
            .catch(error => {
                document.getElementById('result').innerHTML =
                    '<h2 style="color: red;">ERROR!</h2>' +
                    '<p>' + error.message + '</p>';
            });
    </script>
</body>
</html>
    """
    return HttpResponse(html_content, content_type='text/html')


def serve_media_with_fallback(request, path):
    """
    Serve media files with fallback for missing images.
    Returns a placeholder image for missing image files.
    """
    # Check if the requested file exists
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(full_path):
        return serve(request, path, document_root=settings.MEDIA_ROOT)

    # Check if it's an image file (jpg, png, etc.)
    if path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        # Prefer serving a branded placeholder from MEDIA_ROOT if present
        placeholder_candidates = [
            os.path.join(settings.MEDIA_ROOT, 'images', 'placeholder.png'),
            os.path.join(settings.MEDIA_ROOT, 'placeholder.png'),
        ]

        image_data = None
        for candidate in placeholder_candidates:
            if os.path.exists(candidate):
                with open(candidate, 'rb') as f:
                    image_data = f.read()
                break

        # If no file placeholder, return a visible SVG placeholder (renders clearly in browsers)
        if image_data is None:
            svg = (
                "<?xml version='1.0' encoding='UTF-8'?>"
                "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'>"
                "<defs><style>@media(prefers-color-scheme:dark){.bg{fill:#1e1e1e}.fg{fill:#ddd}}@media(prefers-color-scheme:light){.bg{fill:#f3f3f3}.fg{fill:#333}}</style></defs>"
                "<rect class='bg' x='0' y='0' width='400' height='300'/>"
                "<g fill='none' stroke='#bbb' stroke-width='2'>"
                "<rect x='60' y='40' width='280' height='200' rx='8' ry='8'/>"
                "<path d='M90 210 L160 140 L210 190 L270 120 L330 210'/>"
                "<circle cx='230' cy='110' r='18'/></g>"
                "<text class='fg' x='200' y='270' text-anchor='middle' font-family='Arial, sans-serif' font-size='16'>Image not available</text>"
                "</svg>"
            )
            response = HttpResponse(svg, content_type='image/svg+xml; charset=utf-8')
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Content-Disposition'] = 'inline; filename="placeholder.svg"'
            return response

        # Otherwise serve the found placeholder file bytes (PNG)
        response = HttpResponse(image_data, content_type='image/png')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Content-Disposition'] = 'inline; filename="placeholder.png"'
        return response

    # For non-image files, return 404
    raise Http404(f"Media file '{path}' not found.")

def options_view(request):
    """Filter options endpoint - aggregate all options"""
    from apps.images.api.views import (
        GenreOptionViewSet, ColorOptionViewSet, MediaTypeOptionViewSet,
        AspectRatioOptionViewSet, OpticalFormatOptionViewSet, FormatOptionViewSet,
        InteriorExteriorOptionViewSet, TimeOfDayOptionViewSet, NumberOfPeopleOptionViewSet,
        GenderOptionViewSet, AgeOptionViewSet, EthnicityOptionViewSet,
        FrameSizeOptionViewSet, ShotTypeOptionViewSet, CompositionOptionViewSet,
        LensSizeOptionViewSet, LensTypeOptionViewSet, LightingOptionViewSet,
        LightingTypeOptionViewSet
    )

    options_data = {}

    # Get options from each ViewSet
    viewsets = [
        ('genre', GenreOptionViewSet),
        ('color', ColorOptionViewSet),
        ('media_type', MediaTypeOptionViewSet),
        ('aspect_ratio', AspectRatioOptionViewSet),
        ('optical_format', OpticalFormatOptionViewSet),
        ('format', FormatOptionViewSet),
        ('int_ext', InteriorExteriorOptionViewSet),
        ('time_of_day', TimeOfDayOptionViewSet),
        ('numpeople', NumberOfPeopleOptionViewSet),
        ('gender', GenderOptionViewSet),
        ('subject_age', AgeOptionViewSet),
        ('subject_ethnicity', EthnicityOptionViewSet),
        ('frame_size', FrameSizeOptionViewSet),
        ('shot_type', ShotTypeOptionViewSet),
        ('composition', CompositionOptionViewSet),
        ('lens_size', LensSizeOptionViewSet),
        ('lens_type', LensTypeOptionViewSet),
        ('lighting', LightingOptionViewSet),
        ('lighting_type', LightingTypeOptionViewSet),
    ]

    for key, viewset_class in viewsets:
        try:
            queryset = viewset_class.queryset
            if queryset:
                options = list(queryset.values_list('value', flat=True).distinct().order_by('value'))
                options_data[key] = [{"value": opt, "label": opt} for opt in options]
        except Exception as e:
            options_data[key] = []

    return JsonResponse({
        "success": True,
        "data": options_data
    })

urlpatterns = [
    path('', home_view, name='home'),
    path('api/health/', health_view, name='health'),
    path('api/options/', options_view, name='options'),

    path('admin/', admin.site.urls),
    path('api/', include('apps.images.api.urls')),
    path('api/api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/schema/', simple_schema_view, name='schema'),
    path('api/schema/swagger-ui/', custom_swagger_ui_view, name='swagger-ui'),
    path('test-schema/', test_schema_view, name='test-schema'),
] + [
    re_path(r'^media/(?P<path>.*)$', serve_media_with_fallback, name='media'),
]