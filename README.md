# DSE
Scripts to perform Design Space Exploration (DSE) using CyberWorkBench (CWB) High-Level Synthesis tool

Note: in order to run scripts, CyberWorkBench must already be installed and suitable benchmarks (included as .zip) must be specified.

Design Space Exploration is the process of using different parameters to obtain tradeoffs in a design. In this context, High-Level Synthesis is used to rapidly generate RTL descriptions with different area and latency characteristics using a single C++ source code. All of the generated designs are recorded, and those which have the best tradeoffs form the pareto-optimum curve, as can be seen in the ppt slides.

In this project, #pragma directives are used to modify how CWB performs high level synthesis, and Functional Unit (FU) constraints are also modified. The Ant Colony Heuristic is performed and shown to be vastly superior for large designs. 
