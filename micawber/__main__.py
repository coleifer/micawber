import sys

from micawber.providers import refresh_providers


print(refresh_providers(*sys.argv[1:2]))
