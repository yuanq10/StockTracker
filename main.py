import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
