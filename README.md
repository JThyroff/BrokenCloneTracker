##### BrokenCloneTracker

Tracks broken clones on running teamscale instance.

Call ```python main.py --help``` to get help.

##### Approach
This BrokenCloneTracker uses the Teamscale Analysis Platform to keep track of Broken Clones.
To do so it takes a few steps:
1. Read Config: Which project should be analysed?
2. Retrieve AlertCommits from Teamscale Server. These are Commits where Broken Clones are possibly attached.
3. For each Broken Clone: go through all newer commits and check whether the relevant files are affected. If so -> correct the lines of the relevant code region interval and check whether it is affected at this commit.
4. Do the same for the sibling instances of the broken clone instance.
5. Get finding churn for commit and search for relevant the Broken Clone concerning new introduced clone findings
6. Interpret results. Check if both files were affected (or affected critical in the relevant region) or if only one file was affected. 
7. Plot it