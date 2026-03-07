# Admin module does not define its own models.
# Admin uses the Space model from spaces/models.py and User from auth/models.py.
# Import them via their respective service modules only — never import models directly.
