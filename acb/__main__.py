import argparse
import os

from acb import extract_acb, name_gen_default

def name_gen(track):
    print(track)
    return name_gen_default(track)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disarm-with", help="decrypt HCAs with provided keys")
    parser.add_argument("--awb", help="use file as the external AWB")
    parser.add_argument("--no-unmask", action="store_true", default=False,
        help="don't unmask segment names (requires --disarm-with)")
    parser.add_argument("--encoding", default=None, help="file's encoding")
    parser.add_argument("acb_file", help="input ACB file")
    parser.add_argument("output_dir", default=None, nargs="?",
        help="directory to place output files in (default next to the input file)")

    args = parser.parse_args()

    output_dir = args.output_dir
    if not output_dir:
        output_dir = os.path.dirname(args.acb_file) or os.getcwd()

    os.makedirs(output_dir, 0o755, exist_ok=True)
    extract_acb(args.acb_file, output_dir, args.awb, args.disarm_with, name_gen=name_gen, 
        no_unmask=args.no_unmask, encoding=args.encoding)

if __name__ == '__main__':
    main()
