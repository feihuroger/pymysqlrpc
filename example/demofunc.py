# -*- coding: UTF-8 -*-
# standard return

# the simplest example, return one line one row
# return has tow variables, first is colname tuple, second is dataset list
def add(a, b):
    return('sum',), [(a+b,), ]


# return mulit lines mulit rows
# one item in dataset list is tuple, is a line
# size of colname tuple is size of row
# attention , type of one rows  will be same
def cale(a, b):
    return('formula', 'result'), [
        ('add', float(a)+b),
        ('sub', float(a)-b),
        ('mult', float(a)*b),
        ('div', float(a)/b), ]
