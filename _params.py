import argparse


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tp', type=int, default=0, help='The time period tp')
    parser.add_argument('--scen', type=str, default='Gcam', choices=['Gcam', 'GNZ'])
    
    return parser.parse_args()