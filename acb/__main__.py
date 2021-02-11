import argparse
import os

from acb import extract_acb

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--disarm-with", help="decrypt HCAs with provided keys")
    parser.add_argument("--awb", help="use file as the external AWB")
    parser.add_argument("--no-unmask", action="store_true", default=False,
        help="don't unmask segment names (requires --disarm-with)")
    parser.add_argument("acb_file", help="input ACB file")
    parser.add_argument("output_dir", help="directory to place output files in")

    args = parser.parse_args()

    os.makedirs(args.output_dir, 0o755, exist_ok=True)
    extract_acb(args.acb_file, args.output_dir, args.awb, args.disarm_with, no_unmask=args.no_unmask)

if __name__ == '__main__':
    main()
