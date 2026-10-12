# -*- coding: utf-8 -*-
"""Controlla una copia del database delle fatture (sola lettura).

    python3 controlla_copia.py "percorso/della/copia/fatture.db"
"""
import sys

from core.controlla_copia import main

if __name__ == '__main__':
    sys.exit(main(sys.argv))
