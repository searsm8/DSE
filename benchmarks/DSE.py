#!/usr/bin/env python

#DSE.py
#author: Mark Sears
#date: Oct. 2019
#
#Design Space Explorer for HLS
#
#Provides functions to explore the tradeoffs in the HLS design space.
#Calls different binaries of CyberWorkBench (CWB) to synthesize designs.
#Area and Latency of a design given different CWB settings can be compared.
#
#The primary functions are:
#
#exh_FU_search()
#exhaustively searches the design space for Functional Units
#
#exh_Pragma_search()
#exhaustively searches the design space for Pragmas
#
#ant_Pragma_search()
#uses the Ant Colony heuristic to efficiently search the design space

import os
import sys
import CWB
import time
import pdb
import random

def exh_FU_search(name="sobel", iteration=1):
	'''
	run bdltran repeatedly for different FU constraints of L:M:S
	begin at [L, M, S] = [1, 1, 1] and increment FUs
	until no changes in area are seen
	'''

	print("\n********Begin exhaustive FU search for design \"" + name + "\"********")
	start = time.time()
	CWB.bdlpars(name)

	fcnt = [1,1,1] #defines number of FU allowed (Large, Med, Small)
	fcnt_to_inc = 2 #index of the fcnt (L, M, S) which will be incremented
	exhausted = False #flag to stop the search when no more change is seen
	method = "FU" #tag which indicates we are exploring the design space with FUs 

	CWB.bdltran_gen_fcnt(name, fcnt) #create a new .FCNT file
	CWB.bdltran(name) #run once to initialize area and latency values
	initial_result = CWB.get_results_str(name, method, iteration, "unconstrained")
	initial_area = initial_result.split(",")[3]
	initial_latency = initial_result.split(",")[21]

	CWB.bdltran_gen_fcnt(name) #create a new .FCNT file
	CWB.bdltran(name) #run once to initialize area and latency values
	unconstrained_result = CWB.get_results_str(name, method, iteration, "unconstrained")

	results, new_area, new_latency = [], [initial_area]*3, [initial_latency]*3
	prev_area, prev_latency = [0]*3, [0]*3

	#create results file
	os.system(r"mkdir " + name + "/results > misc_err.log 2> misc_err.log")
	results_file_name = name + "/results/" + name + "_FU_search_results.CSV"
	header = "Method,Iteration,ATTR,AREA,state,FU,REG,MUX,DEC,pin_pair,net,max,min,ave,MISC,MEM,cp_delay,sim,Pmax,Pmin,Pave,Latency,BlockMemoryBit,DSP\n"
	printToFile(results_file_name, header, "w")	
	printToFile(results_file_name, unconstrained_result)	
	
	run_count = 0
	#primary while loop that calls bdltran
	#changes .FCNT file each iteration, and then synthesizes the design.
	while(not exhausted):
		CWB.bdltran_gen_fcnt(name, fcnt) #create a new .FCNT file
		CWB.bdltran(name)

		#append results to string
		attr = "L" + str(fcnt[0]) + ":M" + str(fcnt[1]) + ":S" + str(fcnt[2])
		new_result = CWB.get_results_str(name, method, iteration, attr)
		new_area[fcnt_to_inc] = new_result.split(",")[3]
		new_latency[fcnt_to_inc] = new_result.split(",")[21]

		run_count += 1
		print("Run #" + str(run_count) + ": finished bdltran for constraints [" + attr + "]")
		split = new_result.split(",")
		area, latency = split[3], split[21]
		print("Area: " + area + "\tLatency: " + latency)


		#if there has been no change in the area and latency, move to the next stage
		if(new_area[fcnt_to_inc] == prev_area[fcnt_to_inc] and \
				new_latency[fcnt_to_inc] == prev_latency[fcnt_to_inc]): 
				if(fcnt_to_inc == 0): #gone through all possibilities! end search
					exhausted = True	
				if(fcnt_to_inc == 1):
					fcnt_to_inc = 0
					fcnt[2] = 1
					fcnt[1] = 1
				if(fcnt_to_inc == 2):
					fcnt_to_inc = 1
					fcnt[2] = 1
		else: #else it is a new result!
			if(fcnt_to_inc < 2):
				fcnt_to_inc = 2
			printToFile(results_file_name, new_result)

		prev_area[fcnt_to_inc], prev_latency[fcnt_to_inc] = new_area[fcnt_to_inc], new_latency[fcnt_to_inc]
		#increment the FUs to be different
		fcnt[fcnt_to_inc] = fcnt[fcnt_to_inc] + 1
	#end while

	print("\n******Results written to: " + results_file_name)
	end = time.time()
	runtime = "Execution time for exh_FU_search(): " + str(end-start)
	print(runtime)
	printToFile(results_file_name, runtime)
#end exh_FU_search()


def exh_pragma_search(name="sobel", iteration=1):
	'''
	Performs an exhaustive search of pragmas for the designated design
	Looks for a file "lib_<name>.info" which has an attribute library for pragmas
	Calls CWB bdlpars to synthesize designs using every possible combination of pragmas
	'''

	print("\n********Begin exhaustive pragma search for design \"" + name + "\"********")
	start = time.time()
	
	#create output file
	os.system(r"mkdir " + name + "/results > misc_err.log 2> misc_err.log")
	results_file = name + "/results/" + name + "_exh_pragma_search_results.CSV"
	header = "Method,Iteration,ATTR,AREA,state,FU,REG,MUX,DEC,pin_pair,net,max,min,ave,MISC,MEM,cp_delay,sim,Pmax,Pmin,Pave,Latency,BlockMemoryBit,DSP\n"
	printToFile(results_file, header, "w")


	#read pragma library into array structure
	pragma_lib_file = open(name+"/lib_"+name+".info", "r")

	attr = [] #holds all possible attributes for pragmas
	for line in pragma_lib_file:
		if(line[0] != "#" and len(line) > 4): #skip comments and blank lines
			index = int(line[4]+line[5])
			while(index > len(attr)-1):
				attr.append([]) #ensure attr has enough room!
			attr[index].append(line)
	header_name = name+"/attrs.h"

	#massage the attr strings to match the CWB syntax
	for i, group in enumerate(attr):
		for j, string in enumerate(group):
			split_str = string.split(" ")
			if( "EXPAND" in split_str[2] ):
				split_str[2] = split_str[2][0:-1] #remove the \n character
				split_str.append(", array_index=const\n")
			split_str.insert(2, "=")
			split_str.insert(1, "Cyber")
			split_str.insert(0, "#define")
			attr[i][j] = " ".join(split_str)
	
	attr_indices = [0]*len(attr) #tracks the current attrs being used

	exhausted = False #flag to stop the search when no more change is seen
	method = "PRG" #tag which indicates we are exploring the design space with pragmas
	run_count = 0
	#primary while loop that calls bdltran
	#changes pragmas each iteration, and then synthesizes the design.
	#repeat until all possible pragma combinations are sythesized
	#this might take a while to complete!
	while(not exhausted):
		options = "" #extra options to pass to bdltran
		#change the header file attrs.h to a new combination based on attr_indices
		for i in range(1, len(attr)):
			if(i == 1): mode = "w" #on the first line, use write option to overwrite old file
			else: mode = "a" #on all other lines, append to file
			
			printToFile(header_name, attr[i][attr_indices[i]], mode)
			if("folding" in attr[i][attr_indices[i]]):
				options	= "" #" -ZZpipeline "

		bdl_start = time.time()
		#run CWB bdltran, record results
		CWB.bdlpars(name)
		CWB.bdltran_gen_fcnt(name) #create a new .FCNT file for the new parse
		CWB.bdltran(name, options)	
		bdl_end = time.time()
	
		attr_hash = "" #string representing which pragmas are chose for this run
		for num in attr_indices:
			attr_hash = attr_hash + str(num)
		new_result = CWB.get_results_str(name, method, iteration, attr_hash)
		printToFile(results_file, new_result)

		run_count +=1
		print("Run #" + str(run_count) + ": finished bdltran for attr_hash = " + attr_hash)
		split = new_result.split(",")
		if(len(split) > 21): area, latency = split[3], split[21]
		else: area, latency = '',''
		print("Area: " + area + "\tLatency: " + latency)

		#update indices to a new attr combination
		for i in range(len(attr_indices)-1, 0, -1):
			if(attr_indices[i] == len(attr[i])-1):
				attr_indices[i] = 0 
				#if(i == len(attr_indices)-1):
				if(i == 1):
					exhausted = True #all combinations have been tried!
			else:
				attr_indices[i] += 1 
				break

	#end while(not exhausted)

	print("\n******Results written to: " + results_file)
	end = time.time()
	runtime = "Execution time for exh_pragma_search(): " + str(end-start)
	print(runtime)
	printToFile(results_file, runtime)
#end exh_pragma_search()

#HYPERPARAMTERS
#the following hyperparameters can be used to tune the ACO ant algorithm
#experimenting with different values may yield drastically different results

ants_per_pragma = 20  #determines how many ants are created for each pragma to be explored
phero_per_move = 10.0/ants_per_pragma #increase pheromones by this amount for each ant move to a location
phero_evap_rate = .3 #defines how fast pheromones evaporate.
			#e.g. .1 means 10% of pheromones evaporate after each move
convergence_criteria = .7 #the proportion of pheromones that must be reached to reach convergence
end_criteria = 0.98 #if there are very few new designs found by ants, it is critiria to end

area_weight = .5 #how much to favor the area or latency of the design?
latency_weight = .5
min_attractiveness = 1  # the smallest allowed attractiveness for a pragmas to have. Prevents pragmas from being discarded prematurely.
	
class Ant:
	'''
	Ants are used for the Ant Colony Optimization heuristic (ACO).
	Each ant is trying to find food (a good solution) by exploring the design space.
	Initially ants move about randomly, dropping pheromones as they go.
	As better solutions are found, more pheromones are left there.

	Each ant has a "position" with n dimensions, where n is the number of pragmas being explored
	at each step, an ant will change its position in a single dimension and leave pheromones and 
	make it more likely that other ants will follow their step.
	'''
	
	def __init__(self, attr, ID):
		self.ID = ID
		self.pos = [0] #the position of the ant
		#each ant starts in a random position in the attribute space
		for i in range(1,len(attr)):
			self.pos.append(random.randrange(0,len(attr[i])))


	def move(self, pheromones, cost): 
		print("\nPerforming move for ant #" + str(self.ID))
		#based on the ant's current position and the pheromone levels, choose a move	
		#choose a random dimension to move in (i.e. which pragma will change)
		dim = random.randrange(1,len(pheromones)) #randomly choose a dimension for this ant to change

		#define attractiveness for each potential move
		#A = max(1, Ph - QoR + 1)
		#minimum attraction is 1 to allow random moves
		attractiveness = []	
		for i in range(len(cost[dim])):
			attractiveness.append(max(min_attractiveness , pheromones[dim][i] - cost[dim][i] + 1))

		#choose a new pragma to "move" to. use the pheromones and cost as weights
		roll = random.random()*(sum(attractiveness))
		choice = 0
		while(True):
			roll -= attractiveness[choice]
			if(roll <= 0):
				break
			choice += 1
		#choice = random.randrange(len(pheromones[dim]))

		self.pos[dim] = choice #performs the selected move

		#update the pheromones based on the move made
		pheromones[dim][choice] += phero_per_move
		return pheromones


	def eval_position(self, name,  attr, QoRs, min_area, max_area, min_latency, max_latency, results_file, iteration = 0):
		#evaluate the ant's current position 
		#run CWB commands to produce a new design and extract area and latency
		#return a Quality of Result (QoR) metric
		#the QoR is a normalized combination of the area and latency of a design
	
		#check if this ant's position has already been evaluated
		#to avoid repeating the same work
		pos_hash = get_attr_hash(self.pos)
		prev_QoR = QoRs.get(pos_hash) 
		if(prev_QoR != None):
			return (prev_QoR, -1, -1)


		#else, need to run CWB
		#modify the attr.h file according to the ant's position
		header_name = name+"/attrs.h"
		for i in range(1, len(attr)):
			if(i == 1): mode = "w" #on the first line, use write option
			else: mode = "a" #on all other lines, append to file
			printToFile(header_name, attr[i][self.pos[i]], mode)

		#run CWB bdltran, record results
		print(self.pos)
		print("Ant # " + str(self.ID) + ": Running CWB for new design...")
		CWB.bdlpars(name)
		CWB.bdltran_gen_fcnt(name) #create  new .FCNT file for the new parse
		CWB.bdltran(name)	

		method = "ANT"
		new_result = CWB.get_results_str(name, method, iteration, pos_hash)
		if(new_result == ""): #if result is blank, there was an error
			return (9, -1, -1) # cost of 9 means 9 times worse than avg
		#write the new result to file
		printToFile(results_file, new_result, "a")


		result_split = new_result.split(",")
		if(len(result_split) > 0):
			area = float(result_split[3]) 
			latency = float(result_split[21])
		else:  #if no result was obtained, give this a really bad result so ants avoid it
			area = max_area*1
			latency = max_latency*1

		if(max_area == 0):
			max_area = area
			max_latency = latency

		norm_area = float(area - min(min_area, area)) / float(max(max_area, area) - min(min_area, area))
		norm_latency=float(latency - min(min_latency, latency)) / float(max(max_latency, latency) - min(min_latency, latency))

		#to compute the QoR, must normalize the area and latency to their avgs
		#QoR is a measure of how good the design is so that ants can tell which
		#they want to go towards. lower area is good. lower latency is good.
		QoR = float(norm_area)*area_weight + float(norm_latency)*latency_weight

		#if the result is perfectly average, the QoR will be 1
		#less than 1 indicates a GOOD design, with low area and latency
		#greater than 1 indicates a below average design
		return (QoR, area, latency)
#end class Ant

def phero_evap(pheromones):
	'''
	simulates the evaporation of pheromones over time.
	when a path is not taken, the amount of pheromones slowly decreases
	'''
	print("phero_evap!")
	for pragma in range(1, len(pheromones)):
		for index in range(len(pheromones[pragma])):
			pheromones[pragma][index] *= 1-phero_evap_rate
			#pheromones[pragma][index] = max(0, pheromones[pragma][index] - phero_evap_rate)

	for i in range(1, len(pheromones)):
		print(pheromones[i])
	return pheromones
#end phero_evap 

def get_attr_hash(attr):
	my_hash = "" #string representing which pragmas are chose for this run
	for num in attr:
		my_hash = my_hash + str(num)
	return my_hash

def ant_pragma_search(name="sobel", iterations = 1):
	'''
	Performs an efficient search of pragmas for the designated design using the Ant Colony heuristic.
	Looks for a file "lib_<name>.info" which has an attribute library for pragmas
	Calls CWB bdlpars to synthesize designs using pragmas determined by the heuristic 
	'''

	print("\n********Begin Ant Colony DSE Heuristic for design \"" + name + "\"********")
	start = time.time()
	
	#create output file
	os.system(r"mkdir " + name + "/results > misc_err.log 2> misc_err.log")
	results_file = name + "/results/" + name + "_ant_"+ str(ants_per_pragma) + "_evap-"+ str(phero_evap_rate) + "_end-" + str(end_criteria) + ".CSV"
	header = "Method,Iteration,ATTR,AREA,state,FU,REG,MUX,DEC,pin_pair,net,max,min,ave,MISC,MEM,cp_delay,sim,Pmax,Pmin,Pave,Latency,BlockMemoryBit,DSP\n"
	printToFile(results_file, header, "w")

	#read pragma library into array structure
	pragma_lib_file = open(name+"/lib_"+name+".info", "r")

	attr = [] #holds all possible attributes for pragmas
	for line in pragma_lib_file:
		if(line[0] != "#" and len(line) > 4): #skip comments and blank lines
			index = int(line[4] + line[5])	
			while(index > len(attr)-1):
				attr.append([]) #ensure attr has enough room!
			attr[index].append(line)

	#massage the attr strings to match the CWB syntax
	for i, group in enumerate(attr):
		for j, string in enumerate(group):
			split_str = string.split(" ")
			if(split_str[2] == "EXPAND"):
				split_str.append(", array_index=const")
			split_str.insert(2, "=")
			split_str.insert(1, "Cyber")
			split_str.insert(0, "#define")
			attr[i][j] = " ".join(split_str)

	method = "ANT"#tag which indicates we are exploring the design space with Ant colony ACO
	#primary while loop that calls bdltran
	#changes pragmas each iteration, and then synthesizes the design.
	#repeat until all possible pragma combinations are sythesized
	#this might take a while to complete!
	
	for iteration in range(int(iterations)):
		convergence = False #flag to stop the search when no more change is seen

	#create a group of ants which will sniff out the best pragmas!
	#initially ants wander aimlessly
		print("*******Begin Ant Colony Iteration #" + str(iteration) + "*******")
		print("\nCreating " + str((len(attr)-1)*ants_per_pragma) + " ants...\n")
		ants = []
		for dim in range(1, len(attr)):
			for i in range(ants_per_pragma):
				ants.append(Ant(attr, len(ants)))
	
		design_count = 0
		min_area, max_area, min_latency, max_latency = 0, 0, 0, 0

		moves_without_change = 0 #track how many ant moves occur without finding a new design. Used for exit criteria
	#initialize pheromones
		pheromones = []
		for dim in range(len(attr)):
			pheromones.append([0]*len(attr[dim]))

	#initialize cost
		cost = []
		for dim in range(len(attr)):
			cost.append([0]*len(attr[dim])) #initialize to very large cost value

	#count the number of times each pragma is used
		prag_count = []
		for dim in range(len(attr)):
			prag_count.append([0]*len(attr[dim]))

		QoRs = {}
		move_count = 0
		print("Begin Ant Colony iteration #" + str(iteration))

		while(not convergence):

			move_count += 1
			print("Beginning move epoch #" + str(move_count))
			moves_without_change = 0
		#	if(move_count % 1000 == 0):
		#		pdb.set_trace()
			for i in range(len(ants)): #ant move loop
				#for each ant, perform a move on a random pragma
				pheromones = ants[i].move(pheromones, cost)
				#evaluate the ants current position
				new_QoR, new_area, new_latency = ants[i].eval_position(name, attr, QoRs, min_area, max_area, min_latency, max_latency, results_file, iteration)
				myhash = get_attr_hash(ants[i].pos)
				cost = updateCost(cost, ants[i].pos, new_QoR, prag_count)
				QoRs[myhash] = new_QoR
			
			#keep a running avg of the area and latency metrics
			#so that the quality of solutions can be evaluated
				if(new_area > 0):
					design_count += 1
					if(min_area == 0): min_area = new_area
					if(min_latency == 0): min_latency = new_latency
					if(new_area < min_area): min_area = new_area
					if(new_area > max_area): max_area = new_area
					if(new_latency < min_latency): min_latency = new_latency
					if(new_latency > max_latency): max_latency = new_latency
				else: moves_without_change += 1
			#end ant move loop

			#EXIT CRITERIA
			'''check if convergence has been met.
			if very few new moves were made, exit!
			'''	
			if(moves_without_change >= end_criteria*len(ants)):
				convergence = True 

			'''Or, if pheromones are very strong on a single pragma in all dimensions, 
			then ants are unlikely to move away from the high concentration.
			Therefore, check if pheromones are heavily concentrated, indicating convergence
			'''	
			not_converged_count = 0
			for dim in range(1, len(pheromones)):
			#if 70% of pheromones are in one spot, this pragma has converged
				if(float(max(pheromones[dim]) / (sum(pheromones[dim])+0.01)) < convergence_criteria):
					not_converged_count += 1
			#if nearly all pragmas are converged, exit
			if(not_converged_count <= len(pheromones)/8):
				convergence = True # if (most) pragmas have converged, exit!

			pheromones = phero_evap(pheromones )

		#end while(not convergence)

	print("\n******Results written to: " + results_file)
	end = time.time()
	runtime = "Execution time for ant_pragma_search(): " + str(end-start)
	print(runtime)
	printToFile(results_file, runtime)


#end ant_pragma_search()

def updateCost(cost, position, QoR, prag_count):
	#Given the QoR, update the cost at the given positions
	for i, pos in enumerate(position):
		if(i == 0): continue
		prag_count[i][pos] += 1
		if(cost[i][pos] == 0):
			cost[i][pos] = QoR
		else: #use the running average
			cost[i][pos] += (QoR - cost[i][pos])/prag_count[i][pos]

	return cost

#end updateCost

def printToFile(file_path, str_to_print, mode="a"):
	'''
	utility function to open, print to file, close
	useful to keep intermediate results without having to finish a process
	'''
	out_file = open(file_path, mode)
	out_file.write(str_to_print)
	out_file.close()
#end printToFile()

def displayHelp():
	'''
	provide the user with a description of the DSE, what it does, and how to use it.
	'''

	print("\n######## Welcome to the High Level Synthesis (HLS) Design Space Explorer (DSE)!")
	print("By changing 'knobs' such as Functional Units (FU) and pragmas before synthesis, many different implementations can be achieved automatically and the best one selected based on area and latency.")
	print("To run an exploration, simply hit ENTER to return to the Main Menu, select a design and an exploration methodology.")
	print("********NOTE: this DSE looks for target designs in subfolders of the correct name. It should be executed from the 'benchmarks' folder.\n")
	print("There are 3 different types of runs in this DSE:\n")
	print("1) Functional unit exhaustive search. This option tries every possible combination of FUs for the design. It begins with 1 of each kind of FU and slowly increments them until no change in the design is seen.\n")
	print("2) Pragma Exhaustive search. This option looks for a '.info' file with a library of pragmas to try. It then inserts those pragmas into a header file which changes the way the source files are synthesized. It tries every possible combination of pragmas.\n")
	print("********NOTE: Exhaustive searches can take a very long time for large designs. The exhaustive searches are only intended to be run on relatively small designs.\n")
	print("3) Heuristic Pragma exploration. This option allows for 'good' designs to be found faster and with less effort. In this DSE, the Ant Colony Optimization heuristic is used. While it does not guarantee that the best design will be found, it finds many good designs in significantly less time. For larger designs, heuristics must be used for DSE to be practical.\n")
	print("Hit ENTER when you are ready to continue. Happy exploring!")
	raw_input() #wait for ENTER

def mainMenu():
	'''
	provide a menu for ease of use, and to look good for the professor
	'''
	while(1):
		print("\n********HLS Design Space Explorer Main Menu********")

	#provide options to select one of 5 designs, or else enter a new design name
		print("\nSelect a design:")
		print("1) ave16")
		print("2) sobel")
		print("3) kasumi")
		print("4) interpolation")
		print("5) decimation")
		print("h) Help Menu.")
	
		design_num = raw_input("Select: ")

		if(design_num == 'h'):
			displayHelp()
			mainMenu()
			return
	#provide options between FU search, pragma search, or ant colony heuristic
		print("\nSelect a search option:")
		print("1) Exhaustive FU search")
		print("2) Exhaustive pragma search")
		print("3) Ant Colony pragma optimization heuristic ")
		
		search_type = raw_input("Select:")
	

		#perform the task selected
		if(design_num == "1"): design_name = "ave16"
		elif(design_num == "2"): design_name = "sobel"
		elif(design_num == "3"): design_name = "kasumi"
		elif(design_num == "4"): design_name = "interpolation"
		elif(design_num == "5"): design_name = "decimation"
		else: design_name = design_num

		if(search_type == "1"): exh_FU_search(design_name)
		elif(search_type == "2"): exh_pragma_search(design_name)
		elif(search_type == "3"):
			iterations = raw_input("Run Ant Colony for how many iterations?\n")
			ant_pragma_search(design_name, iterations)
		else: print("Invalid search option!")

		#ask for another run
		print("\nRun complete!")
		again = raw_input("\nRun again? (y/n): ")
		if(again != "y"):
			break	
		

	#end while(1)
#end mainMenu()


#code that runs on startup
#check for options
if len(sys.argv) > 1:
	if(sys.argv[1] == '-h'):
		displayHelp()
mainMenu()


