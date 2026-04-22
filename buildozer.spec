[app]
title = Weather Insight Hub
package.name = weatherhub
package.domain = org.insight
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

# (list) Application requirements
# Added requirements for Flet stability
requirements = python3, flet==0.21.0, flet-geolocator, requests, pyjnius

# (list) Permissions
android.permissions = ACCESS_FINE_LOCATION, INTERNET

# (int) Android API to use
android.api = 33
android.minapi = 21
# android.sdk = 33

# (str) Supported orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) List of service to declare
# services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

# (str) Custom source guard for requirements
# requirements.source.requests = ...

# (str) The Android Arch to build for, choices: armeabi-v7a, arm64-v8b, x86, x86_64
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
