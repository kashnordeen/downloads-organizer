import sys

if "--verify-bundle" in sys.argv:
    import traceback
    from pathlib import Path
    report = sys.argv[sys.argv.index("--verify-bundle") + 1]
    try:
        from organizer.bundle_check import verify
        verify(report)
    except Exception:
        Path(report).write_text(traceback.format_exc(), encoding="utf-8")
        sys.exit(1)
else:
    from organizer.app import main
    main()
