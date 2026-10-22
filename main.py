import sys

if __name__ == '__main__':
    if '--gui-self-test' in sys.argv:
        from ultimate_updater.gui_selftest import main
        raise SystemExit(main())
    if '--self-test' in sys.argv:
        from ultimate_updater.selftest import main
        raise SystemExit(main())
    from ultimate_updater.gui import main
    raise SystemExit(main())
