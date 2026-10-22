import sys

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        from ultimate_updater.selftest import main
        raise SystemExit(main())
    from ultimate_updater.gui import main
    raise SystemExit(main())
