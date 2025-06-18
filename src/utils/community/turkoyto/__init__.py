# Initialize the turkoyto_views package
import os

# Create the directory if it doesn't exist
os.makedirs(os.path.dirname(__file__), exist_ok=True)

# This file is required to make the directory a Python package
from .ticket_views import TicketButton, TicketModal, TicketCloseView
