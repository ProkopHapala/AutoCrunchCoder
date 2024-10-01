
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyCruncher import ctags as ct

src_path = "/home/prokophapala/git/FireCore/cpp"

exclude = ["common_resources", "Build", "Build-asan", "Build-opt", "Build-dbg"]

#ct.run_ctags("tags_all.json", src_path, exclude=exclude)       # Generate ctags JSON file

ct.process_ctags_json_prokop("tags_all.json", src_path )


# json_file = 'tags_all.json'  # Replace with the actual JSON file path
# class_details = ct.parse_ctags_json(json_file)
# ct.display_class_details(class_details)







# Analyze dependencies and generate markdown report
#dependency_graph, class_deps, function_deps, file_deps, files_dict, classes_dict = ct.analyze_dependencies("tags_all.json", "firecore_dependencies.md")

# # Print some basic statistics
# print(f"\nNumber of classes: {len(classes_dict)}")
# print(f"Number of functions: {len(function_deps)}")
# print(f"Number of files: {len(files_dict)}")

# # Print sample of class dependencies
# print("\nSample of class dependencies:")
# for cls, deps in list(class_deps.items())[:5]:
#     print(f"{cls}: {deps}")  # deps is already a set, no need to sort

# # Print sample of function dependencies
# print("\nSample of function dependencies:")
# for func, deps in list(function_deps.items())[:5]:
#     print(f"{func}: {deps}")  # deps is already a set, no need to sort

# # Print sample of file dependencies
# print("\nSample of file dependencies:")
# for file, deps in list(file_deps.items())[:5]:
#     print(f"{file}: {deps}")  # deps is already a set, no need to sort

# print("\nMarkdown report has been generated: firecore_dependencies.md")

# # Print some basic statistics about the dependency graph
# print(f"Number of nodes in the dependency graph: {dependency_graph.number_of_nodes()}")
# print(f"Number of edges in the dependency graph: {dependency_graph.number_of_edges()}")

# # Print the top 5 most connected nodes
# degree_centrality = sorted(nx.degree_centrality(dependency_graph).items(), key=lambda x: x[1], reverse=True)[:5]
# print("\nTop 5 most connected nodes:")
# for node, centrality in degree_centrality:
#     print(f"{node}: {centrality:.4f}")

# # Process and print sample of file and class dictionaries
# files_dict, classes_dict = ct.process_ctags_json("tags_all.json")
# print("\nSample of file dependencies:")
# ct.print_file_dict({k: files_dict[k] for k in list(files_dict)[:5]}, end="\n")

# print("\nSample of class dependencies:")
# ct.print_class_dict({k: classes_dict[k] for k in list(classes_dict)[:5]}, end="\n")


# for k,v in files_dict.items():
#     print("file: ", k)
#     print('== classes')
#     for m in v['classes'  ]: print("    ", m)
#     print('== functions')
#     for f in v['functions']: print("    ", f)
#     print('== globals')
#     for g in v['globals'  ]: print("    ", g)

# for k,v in classes_dict.items():
#     print("class: ", k)
#     print("== Methods:");
#     for m in v['methods'   ]: print("   ", m)
#     print("== properties:");
#     for p in v['properties']: print("   ", p)

#ct.generate_ctags_files( src_path, exclude = exclude )

#files_dict, classes_dict = ct.construct_dictionaries()

# Display the results
# import pprint
# pprint.pprint(files_dict)
# pprint.pprint(classes_dict)
