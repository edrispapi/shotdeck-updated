from rest_framework import serializers
from apps.decks.models import Deck

class DeckSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    # Add tags field for input
    tags = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of tags to find images for this deck"
    )

    # Add computed field for image count
    image_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Deck
        fields = [
            'id',
            'title',
            'description',
            'owner',
            'owner_username',
            'image_slugs',
            'tags',  # Write-only field for tag input
            'image_count',  # Read-only computed field
            'created_at',
            'updated_at'
        ]
        read_only_fields = ('owner', 'owner_username', 'created_at', 'updated_at', 'image_count')

    def get_image_count(self, obj):
        """Return the count of images in this deck"""
        return len(obj.image_slugs) if obj.image_slugs else 0

    def create(self, validated_data):
        """Enhanced create method to fetch images based on tags"""
        tags = validated_data.pop('tags', [])

        # Create the deck first
        deck = super().create(validated_data)

        if tags:
            # Fetch images from image service based on tags
            image_slugs = self._fetch_images_by_tags(tags)
            if image_slugs:
                deck.image_slugs = image_slugs
                deck.save()

        return deck

    def _fetch_images_by_tags(self, tags):
        """Fetch image slugs from image service based on tags"""
        # For now, return mock data to avoid requests dependency
        # TODO: Implement proper API call when requests is available
        mock_slugs = [
            f"mock-image-{i}" for i in range(min(len(tags) * 3, 20))
        ]
        print(f"Mock: Would fetch images for tags: {tags}")
        print(f"Mock: Returning slugs: {mock_slugs}")
        return mock_slugs