import cProfile
import pstats
from mpf.commands import both

cProfile.run('both._start_mc("/Users/avanwink/python3/bin/mpf", "/Users/avanwink/git/me", ["-c","config,stealth"])', 'profiler/restats')
