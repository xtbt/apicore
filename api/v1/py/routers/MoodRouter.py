"""Mood routes: only wires the `moods` URLs to MoodController."""
from controllers.MoodController import MoodController


def register_mood_routes(router):
    router.add_crud_routes('/moods', MoodController, 'Mood', public=True)
