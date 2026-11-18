"""Mood routes: only wires the `moods` URLs to MoodController (all protected)."""
from controllers.MoodController import MoodController


def register_routes(router):
    router.add_crud_routes('/moods', MoodController, 'Mood')
