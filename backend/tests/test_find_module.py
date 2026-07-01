import sys
try:
    import firebase_admin
    print("FIREBASE_ADMIN IS:", firebase_admin)
    print("FIREBASE_ADMIN FILE:", getattr(firebase_admin, '__file__', 'no file'))
    print("FIREBASE_ADMIN PATH:", getattr(firebase_admin, '__path__', 'no path'))
except Exception as e:
    print("ERROR IMPORTING:", e)
print("SYS PATH IS:", sys.path)
