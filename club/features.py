# FEATURE-FLAGS
# Use them to enable/disable different functions
# We recommend to create new feature-flags if you want to add new features or disable existing ones in your fork
# That way you can add them to the upstream (github.com/vas3k/vas3k.club) for better sync in the future

# Hide posts feed (main page) from unauthorized users
#   True — feed is only visible to club members, other users will be redirected to landing page
#   False — everyone can view the feed, it becomes the main page
PRIVATE_FEED = True

# Enable auth and payment via Patreon
#   See settings.py for more configs (PATREON_ - prefixed)
PATREON_AUTH_ENABLED = False
