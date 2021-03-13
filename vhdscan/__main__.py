import argparse
from lib import application

if __name__ == "__main__":
    def run():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--version",
            help="prints version",
            action="store_true",
        )
        parser.add_argument(
            "path",
            help="path to project folder to open",
            type=str,
            nargs="?",
            default="",
            metavar="<path>",
        )
        args = parser.parse_args()

        if args.version:
            print("%s %s" % (parser.prog, application.version))
        else:
            application.run(args.path)

    run()
