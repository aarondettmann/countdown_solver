#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Solve the mathematical puzzles of the game show Countdown.

Input (on the command line):

* A target number and 6 (smaller) numbers.

The goal is to obtain a result as close to the target as possible, by
performing arithmetic operations (+, -, x, /) on the 6 numbers (not all need to
be used). The numbers and operations can be chosen in any order, but at each
stage the intermediary result has to be a positive integer.

Output:

* All results closest to the target. Results with fewer numbers are listed
  first. The results are unique (but some can be equivalent if associativity is
  taken into account).

Requires Python 3.6 or higher.
"""

import argparse
import sys
from functools import lru_cache
from itertools import combinations, product, zip_longest

assert sys.version_info >= (3, 6)

PROG_NAME = 'CountdownSolver'


class Solutions:

    def __init__(self, numbers):
        """
        Create all valid arithmetic operations between numbers out of a given tuple

        Args:
            :numbers: tuple of numbers of length n

        Attrs:
            :all_groups: dictionary, where keys are all unique combinations of
                         numbers of lengths 1 to n, and the values are the
                         corresponding instances of class 'Group'
        """

        self.all_numbers = numbers
        self.size = len(numbers)
        self.all_groups = self._unique_groups()

    def _unique_groups(self):
        all_groups = {}
        for m in range(1, self.size+1):
            for numbers in combinations(self.all_numbers, m):
                if numbers in all_groups:
                    continue
                all_groups[numbers] = Group(numbers, all_groups)
        return all_groups

    def walk(self):
        """Iterate over all calculations"""
        for group in self.all_groups.values():
            yield from group.calculations


class Group:

    def __init__(self, numbers, all_groups):
        """
        Create a hierarchical tree of groups from a given tuple of numbers

        Args:
            :numbers: tuple of numbers
            :all_groups: dictionary of (smaller) groups that have already been created

        A group is partitioned into all unique unordered pairs of subgroups.

        Example:
        (4, 2, 1, 1) -> [
                (4, 2, 1) + (1),
                (4, 1, 1) + (2),
                (2, 1, 1) + (4),
                (4, 2) + (1, 1),
                (4, 1) + (2, 1)
        ]

        The list of calculations is created by combining the existing
        calculations between each pair of subgroups.

        The calculation of a group (n,) of length 1 is simply the singleton [n]
        """

        self.numbers = numbers
        self.size = len(numbers)
        self.partitions = list(self._partition_into_unique_pairs(all_groups))
        self.calculations = list(self._perform_calculations())

    def __repr__(self):
        return str(self.numbers)

    def _partition_into_unique_pairs(self, all_groups):
        # The pairs are unordered: a pair (a, b) is equivalent to (b, a).
        # Therefore, for pairs of equal length only half of all combinations
        # need to be generated to obtain all pairs; this is set by the limit.
        if self.size == 1:
            return

        limits = (self._halfbinom(self.size, self.size//2),)
        unique_numbers = set()
        for m, limit in zip_longest(range((self.size+1)//2, self.size), limits):
            for numbers1, numbers2 in self._paired_combinations(self.numbers, m, limit):
                if numbers1 in unique_numbers:
                    continue
                unique_numbers.add(numbers1)
                group1, group2 = all_groups[numbers1], all_groups[numbers2]
                yield (group1, group2)

    def _perform_calculations(self):
        if self.size == 1:
            yield Calculation.singleton(self.numbers[0])
            return

        for group1, group2 in self.partitions:
            for calc1, calc2 in product(group1.calculations, group2.calculations):
                yield from Calculation.generate(calc1, calc2)

    @classmethod
    def _paired_combinations(cls, numbers, m, limit):
        for cnt, numbers1 in enumerate(combinations(numbers, m), 1):
            numbers2 = tuple(cls.filtering(numbers, numbers1))
            yield (numbers1, numbers2)
            if cnt == limit:
                return

    @staticmethod
    def filtering(iterable, elements):
        # Filter elements out of an iterable, return the remaining elements
        elems = iter(elements)
        k = next(elems, None)
        for n in iterable:
            if n == k:
                k = next(elems, None)
            else:
                yield n

    @staticmethod
    @lru_cache()
    def _halfbinom(n, k):
        if n % 2 == 1:
            return None
        prod = 1
        for m, l in zip(reversed(range(n+1-k, n+1)), range(1, k+1)):
            prod = (prod*m)//l
        return prod//2


class Calculation:

    def __init__(self, expression, result, is_singleton=False):
        """
        A Calculation consists of an expression (a string) and a result (an
        integer). New calculations are generated from two given calculations,
        by performing arithmetic operations (+, -, x, /) on their results.

        Invalid outcomes (zeroes, negative numbers, fractions, trivial results)
        are ignored. For a single number, the calculation is simply the number
        itself.
        """

        self.expr = expression
        self.result = result
        self.is_singleton = is_singleton

    def __repr__(self):
        return self.expr

    @classmethod
    def singleton(cls, n):
        return cls(f"{n}", n, is_singleton=True)

    @classmethod
    def generate(cls, calca, calcb):
        if calca.result < calcb.result:
            calca, calcb = calcb, calca
        for result, op in cls.operations(calca.result, calcb.result):
            expr1 = f"{calca.expr}" if calca.is_singleton else f"({calca.expr})"
            expr2 = f"{calcb.expr}" if calcb.is_singleton else f"({calcb.expr})"
            yield cls(f"{expr1} {op} {expr2}", result)

    @staticmethod
    def operations(x, y):
        yield (x+y, '+')

        if x > y:  # exclude non-positive results
            yield (x-y, '-')

        if y > 1 and x > 1:  # exclude trivial results
            yield (x*y, 'x')

        if y > 1 and x % y == 0:  # exclude trivial and non-integer results
            yield (x//y, '/')


def cli():
    parser = argparse.ArgumentParser(prog=f'{PROG_NAME}')
    parser.add_argument('target', metavar='TARGET', type=int, help='target number')
    parser.add_argument('numbers', metavar='x1, x2, ...', nargs='+', type=int, help='numbers')
    args = parser.parse_args()

    target = args.target
    unsorted_numbers = args.numbers
    return (target, unsorted_numbers)


def countdown_solver():
    target, unsorted_numbers = cli()
    numbers = tuple(sorted(unsorted_numbers, reverse=True))

    solutions = Solutions(numbers)
    smallest_difference = target
    bestresults = []
    for calculation in solutions.walk():
        diff = abs(calculation.result - target)
        if diff <= smallest_difference:
            if diff < smallest_difference:
                bestresults = [calculation]
                smallest_difference = diff
            else:
                bestresults.append(calculation)
    output(target, smallest_difference, bestresults)


def output(target, diff, results):
    print(f"\nThe closest results differ from {target} by {diff}. They are:\n")
    for calculation in results:
        print(f"{calculation.result} = {calculation.expr}")


if __name__ == "__main__":
    countdown_solver()
