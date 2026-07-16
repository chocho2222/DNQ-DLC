# Data card

The E1 source table contains 200 matched cases per algorithm, paired by benchmark, vehicle count, and simulator seed. The primary binary endpoint is whether the target completes at least one overtake.

Secondary desirable-overtaking proportions assign zero to cases without a completed overtake. Completion time and grass exposure are conditioned on successful cases and are not all-case causal comparisons. N=4-6 is the training vehicle-count range and N=7-8 is extrapolation within the evaluated simulator, not unrestricted generalization.
