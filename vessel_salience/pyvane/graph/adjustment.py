"""Module for changing the topology of a graph created by pyvane.graph.creation. Some heuristics
are used for simplifying the graph and removing small edges."""

from skimage import draw
import networkx as nx
import numpy as np
import pyvane.util as util

def simplify(graph, use_old_method=False, verbose=False):
    """Simplify node positions in a graph, also adjusting the edges. It is assumed that nodes in the
    graph have an attribute 'pixels' containing a list of pixel positions and an attribute 'center',
    containing a single pixel coordinate indicating the position of the node. Also, the edges must have
    a 'path'.

    The simplification works as follows. Since each node represents an object having more than one pixel,
    the associated edges represent branches connected to the border of the object. This function extends the
    path associated to each edge so that it connects to the center position of the node instead of the
    border of the object.

    For instance, consider the following pair of nodes

    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 1 1 0 0 0 0 0 0 0 0 0 0
    0 1 1 1 2 2 2 2 1 1 1 0 0
    0 0 1 0 0 0 0 0 0 1 1 1 0
    0 0 0 0 0 0 0 0 0 0 1 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0

    where 1 indicate pixels associated to the nodes and 2 pixels associated to an edge. If we represent
    the nodes as a single point, we get

    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 0 1 0 2 2 2 2 0 0 0 0 0
    0 0 0 0 0 0 0 0 0 0 1 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0

    Clearly, there is a discontinuity between the node position and the edge path. Thus, the edge is updated
    so that

    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 0 1 2 2 2 2 2 2 0 0 0 0
    0 0 0 0 0 0 0 0 0 2 1 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0
    0 0 0 0 0 0 0 0 0 0 0 0 0

    Note that node attributes are not changed in the process, that is, only the 'path' edge attribute is changed.

    Parameters
    ----------
    graph : networkx.MultiGraph
        Graph to be simplified.
    verbose : bool
        If True, the progress is printed.

    Returns
    -------
    graph_simple : networkx.MultiGraph
        A new graph with modified edges.
    """

    ndim = graph.graph['ndim']

    if verbose:
        print('Simplifying graph...')
        num_edges = graph.number_of_edges()
        print_interv = util.get_print_interval(num_edges)

    graph_simple = graph.copy()

    new_edges = []
    for edge_idx, (node1_idx, node2_idx, key, path) in enumerate(graph_simple.edges(data='path', keys=True)):

        if verbose:
            if edge_idx%print_interv==0 or edge_idx==num_edges-1:
                print(f'\rSimplifying edge {edge_idx+1} of {num_edges}', end='')

        node1 = graph.nodes[node1_idx]
        node2 = graph.nodes[node2_idx]

        if len(node1['pixels'])==1:
            # If node has only one pixel, no need to simplify
            node1_to_path_line = []
        else:
            if use_old_method:
                node1_to_path_line = draw_line_nd_old(node1['center'], path[0])
            else:
                node1_to_path_line = draw.line_nd(node1['center'], path[0], endpoint=False)
            # Remove starting point, which is the same as node1.center
            node1_to_path_line = tuple(coord[1:] for coord in node1_to_path_line)

        if len(node2['pixels'])==1:
            # If node has only one pixel, no need to simplify
            path_to_node2_line = []
        else:
            if use_old_method:
                path_to_node2_line = draw_line_nd_old(path[-1], node2['center'])
            else:
                path_to_node2_line = draw.line_nd(path[-1], node2['center'], endpoint=False)
            # Remove starting point, which is the same as node1.center
            path_to_node2_line = tuple(coord[1:] for coord in path_to_node2_line)

        new_path = list(zip(*node1_to_path_line)) + path + list(zip(*path_to_node2_line))

        graph_simple[node1_idx][node2_idx][key]['path'] = new_path

    return graph_simple

def draw_line_nd_old(p1, p2):
    """Old an extremely inefficient approach for drawing a line. Do not use."""

    p1, p2 = np.array(p1), np.array(p2)
    vet = p2 - p1
    t = np.linspace(0, 1, 1000)
    seg = p1 + vet*np.array([t]).T
    seg = np.round(seg).astype(np.int)

    new_seg = [seg[0]]
    for j in range(1,len(seg)):
        #if ((seg[j][0] != seg[j-1][0]) | (seg[j][1] <> seg[j-1][1]) | (seg[j][2] <> seg[j-1][2])):
        if tuple(seg[j])!=tuple(seg[j-1]):
            new_seg.append(seg[j])

    new_seg.pop(-1)

    return tuple(zip(*new_seg))

def path_length(path, pix_size, img_roi=None):
    """Calculate the arc-length of a parametric sequence of pixels.

    Parameters
    ----------
    path : list of tuple
        A sequence of pixels representing a path/curve.
    pix_size : tuple of float
        The physical size that a pixel represents, can be a different value for each axis.
    img_roi : ndarray
        A region of interest image. Only paths where `img_roi` has value 1 will be considered.

    Returns
    -------
    path_length : float
        The total length of the path.
    """

    dpath = np.diff(path, axis=0)*pix_size
    dlengths = np.sqrt(np.sum(dpath**2, axis=1))

    if img_roi is not None:
        is_inside_roi = img_roi[tuple(zip(*path))]==1
        dlengths = dlengths[is_inside_roi[1:]]

    path_length = np.sum(dlengths)

    return path_length

def add_length(graph):
    """Add arc-length information for all edges in the graph. The graph is modified in-place.
    A new attribute 'length' is added to the edges.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    """

    pix_size = graph.graph['pix_size']
    pix_size = np.array(pix_size)

    for node1, node2, key, path in graph.edges(data='path', keys=True):

        graph[node1][node2][key]['length'] = path_length(path, pix_size)

def add_branch_info(graph):
    """Add branchness information for all edges in the graph. If an edge is incident on at least one
    node with degree 1, it is considered a branch. The graph is modified in-place. A new attirbute
    'is_branch' is added to the edges.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    """

    for node1, node2, key in graph.edges(keys=True):

        if graph.degree(node1)==1 or graph.degree(node2)==1:
            graph[node1][node2][key]['is_branch'] = True
        else:
            graph[node1][node2][key]['is_branch'] = False

def multiedge_iter(graph):
    """Generator for edges that are multiple in the graph, that is, edges connecting pairs of
    nodes that also have other edges between them. Each returned value corresponds to all edge
    between a pair of nodes.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.

    Yields
    ------
    tuple
        A tuple of the form (node1, node2, edge_dict), where edge_dict is a dictionary describing
        each edge between a pair of nodes. Keys in the dictionary are edge indices and the values
        are edge attributes.
    """

    multiple_edges = set()
    for node1, node2, _ in graph.edges:
        if len(graph[node1][node2])>1:
            multiple_edges.add((node1, node2))

    for edge in multiple_edges:
        yield (edge[0], edge[1], graph[edge[0]][edge[1]])

def is_multiple_edge(graph, u, v):
    """Check if two nodes have multiple edges between them.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    u : hashable
        First node.
     v : hashable
         Second node.

    Returns
    -------
    bool
        True if there are multiple edges and False otherwise.
    """

    return len(graph[u][v])>1

def count_multiple_edges(graph):
    '''Count the number of multiple edges between pairs of nodes. Single edges are counted as 0. Two
    parallel edges are counted as 1, and so on.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.

    Returns
    -------
    edge_count : dict
        Dictionary where each key is a tuple associated to an edge (node1, node2) and the values are
        the multiedge count.
    '''

    edge_count = {}
    for node1, node2, _ in graph.edges:
        edge = (node1, node2)
        if edge in edge_count:
            edge_count[edge] += 1
        else:
            edge_count[edge] = 0

    return edge_count

def argmin(values):
    """Return the index of the smallest value of a list.

    Parameters
    ----------
    values : list
        The input list

    Returns
    -------
    index_min : int
        The index of the smallest value in `values`.
    """

    index_min = min(range(len(values)), key=values.__getitem__)
    return index_min

def argmax(values):
    """Return the index of the largest value of a list.

    Parameters
    ----------
    values : list
        The input list

    Returns
    -------
    index_max : int
        The index of the largest value in `values`.
    """

    index_max = max(range(len(values)), key=values.__getitem__)
    return index_max

def get_single_neighbor(graph, node):
    """Return a neighbor of a node. Useful when the node only has one neighbor.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    node : hashable
        The node whose neighbor will be returned.

    Returns
    -------
    hashable
        The neighbor node.
    """

    return list(graph[node].keys())[0]

def get_single_edge_key(graph, node1, node2):
    """Return the key of an edge between two nodes. Useful when the nodes are connected by only one edge.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    node1 : hashable
        The first node.
    node2 : hashable
        The second node.

    Returns
    -------
    hashable
        The edge key.
    """

    return list(graph[node1][node2].keys())[0]

def degree_two_node_type(graph, node):
    """Return the type of a node having degree two. Possible types are

    * 'simple': The node is connected to two other nodes with a simple edge.
    * 'multiple': The node is connected to another node with two (multiple) edges.
    * 'loop': The node has a self-loop.
    * 'unidentified': Connectivity type not recognized.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    node : hashable
        The input node.

    Returns
    -------
    node_type : {'simple', 'multiple', 'loop', 'unidentified'}
        The type of the node.
    """

    neighbors = graph[node]
    node_type = 'unidentified'
    if len(neighbors)==2:
        node_type = 'simple'
    elif len(neighbors)==1:
        neighbor = get_single_neighbor(graph, node)
        if neighbor==node:
            node_type = 'loop'
        if neighbor!=node:
            node_type = 'multiple'

    return node_type

def degree_two_iter(graph, self_loops=True, multiple=True):
    """Generator over all nodes having degree two in the graph.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    self_loops : bool, optional
        If True, also return nodes having a single self-loop edge
    multiple : bool, optional
        If True, also return nodes connected to one other node with two (multiple) edges.

    Yields
    ------
    hashable
        A node with degree two.
    """

    for node, neighbors in graph.adj.items():
        if graph.degree(node)==2:
            node_type = degree_two_node_type(graph, node)
            if node_type=='simple':
                yield node
            if node_type=='loop' and self_loops:
                yield node
            if node_type=='multiple' and multiple:
                yield node

def remove_if_in_list(values, item):
    """Remove `item` in list `values`. Nothing is done if the element is not in the list.  This
    function just calls values.remove(item) while avoiding an exception in case the element is
    not in the list.

    Parameters
    ----------
    values : list
        The input list.
    item : Object
        The item to be removed.
    """

    try:
        values.remove(item)
    except ValueError:
        pass

def remove_small_mul(graph, node1, node2, length_threshold):
    """Remove the *smallest* edge between a pair of nodes having more than one edge between them. The
    edge is not removed if its length is larger than or equal to `length_threshold`.

    Note that the removal of an edge might generate new branches in the graph, but attribute 'is_branch'
    is not updated by this function.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    node1 : hashable
        The first node.
    node2 : hashable
        The second node.
    length_threshold : float
        The threshold to decide if the edge will be removed.

    Returns
    -------
    was_removed : bool
        Indicates if an edge was removed (True) or not (False).
    """

    edges_length = map(lambda x:(x[0], x[1]['length']), graph[node1][node2].items())
    keys, lengths = zip(*edges_length)
    ind_smal_edge = argmin(lengths)
    smallest_length = lengths[ind_smal_edge]
    key_smal_edge = keys[ind_smal_edge]
    if smallest_length<length_threshold:
        graph.remove_edge(node1, node2, key_smal_edge)
        was_removed = True
    else:
        was_removed = False
    return was_removed

def remove_small_mul_all(graph, length_threshold):
    """For pairs of nodes having multiple edges between them, remove all edges having length
    smaller than `length_threshold`. There is only one exception to the removal: when there is
    no edge with length larger than or equal to `length_threshold`, the largest edge is kept.

    If the removal of an edge generates a new branch, attribute 'is_branch' is updated accordingly.

    This function also removes self-loops smaller than `length_threshold`.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    length_threshold : float
        The threshold to decide if the edge will be removed.
    """

    # Remove self-loops smaller than length_threshold
    edges_to_remove = []
    for node1, node2, key, length in nx.selfloop_edges(graph, data='length', keys=True):
        if length<length_threshold:
            edges_to_remove.append((node1, node2, key))

    graph.remove_edges_from(edges_to_remove)

    # Remove multiple edges smaller than length_threshold and that are not the largest among the edges
    # parallel to it
    edges_to_remove = []
    for node1, node2, edges in multiedge_iter(graph):

        edges_length = map(lambda x:(x[0], x[1]['length']), edges.items())
        keys, lengths = zip(*edges_length)
        ind_larg_edge = argmax(lengths)
        largest_length = lengths[ind_larg_edge]
        key_larg_edge = keys[ind_larg_edge]
        for key, edge_attrs in edges.items():
            edge_length = edge_attrs['length']
            if edge_length<length_threshold and key!=key_larg_edge:
                edges_to_remove.append((node1, node2, key))

    graph.remove_edges_from(edges_to_remove)

    add_branch_info(graph)

def two_neighbors_data(graph, node, node_type=None):
    """Given a node having degree 2, returns its neighbors and respective edges. If the node
    has a single neighbor, it means that multiple edges exist between the node and the neighbor.
    In this case, the returned nodes and edges are identical.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    node : hashable
        The reference node.
    node_type : {'simple', 'multiple', 'loop'}, optional
        The type of the node. If not provided, it is calculated by the function.

    Returns
    -------
    tuple of hashable
        A tuple (node1, node2, edge1 key, edge2 key) containing neighbor nodes and respective
        edge keys.
    """

    if node_type is None:
        node_type = degree_two_node_type(graph, node)

    neighbors = list(graph.neighbors(node))
    if node_type=='simple':
        nei1, nei2 = neighbors
        edge1_key = get_single_edge_key(graph, node, nei1)   # Cannot assume key is 0
        edge2_key = get_single_edge_key(graph, node, nei2)
    elif node_type=='multiple':
        nei1 = nei2 = neighbors[0]
        edge1_key, edge2_key = list(graph[node][nei1].keys())
    elif node_type=='loop':
        raise ValueError('Cannot process self-loop.')

    if nei1>nei2:
        # make nei1 always smaller than nei2, for indexing purposes
        nei1, nei2 = nei2, nei1
        edge1_key, edge2_key = edge2_key, edge1_key

    return nei1, nei2, edge1_key, edge2_key

def remove_small_graph_components(graph, length_threshold=20):
    """Remove all edges from connected components obeying the following criterium: the sum of
    edge lengths in the component is smaller than `length_threshold`.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    length_threshold : float
        The threshold to decide if the component will be removed.
    """

    edges_to_remove = []
    for comp in nx.connected_components(graph):
        subgraph = graph.subgraph(comp)
        comp_length = sum(nx.get_edge_attributes(subgraph, 'length').values())
        if comp_length<length_threshold:
            edges_to_remove.extend(subgraph.edges())

    graph.remove_edges_from(edges_to_remove)


def make_new_path(graph, edge1, edge2):
    """Create a new path based on two edges. The new path is a concatenation of
    edge1 path + node center + edge2 path, where node center is the position of the
    node between the two edges. Therefore, it is assumed that `edge1` and `edge2` are
    adjacent.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    edge1 : tuple of hashable
        Tuple of the form (node1, node2, edge key)
    edge2 : tuple of hashable
        Tuple of the form (node1, node2, edge key)

    Returns
    -------
    new_path : list of tuple
        New path containing the pixels of `edge1`, `'edge2' and the node center.
    length_new_path : float
        The length of the newly created path.
    """

    node, nei1, edge1_key = edge1
    node, nei2, edge2_key = edge2

    pix_size = graph.graph['pix_size']
    node_center = graph.nodes[node]['center']

    edge1_attrs = graph[node][nei1][edge1_key]
    edge2_attrs = graph[node][nei2][edge2_key]
    path_nei1 = edge1_attrs['path']
    path_nei2 = edge2_attrs['path']

    if node<nei1:
        # If node<nei1, path runs from node to nei1, we need to reverse that
        path_nei1 = path_nei1[::-1]
    if node>nei2:
        path_nei2 = path_nei2[::-1]

    new_path = path_nei1 + [node_center] + path_nei2

    new_path_seg = np.array([path_nei1[-1], node_center, path_nei2[0]])
    length_new_seg = path_length(new_path_seg, pix_size)
    length_new_path = edge1_attrs['length'] + length_new_seg + edge2_attrs['length']

    return new_path, length_new_path

def branches_to_remove(graph, edge1, edge2, length_threshold):
    """Given two edges, return a list indicating which edge is a branch and have length smaller
    than `length_threshold`. The function might return both edges, only a single edge or an empty list.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    edge1 : tuple of hashable
        Tuple of the form (node1, node2, edge key)
    edge2 : tuple of hashable
        Tuple of the form (node1, node2, edge key)
    length_threshold : float
        The threshold to decide if the edge is a branch to be removed.

    Returns
    -------
    branches_to_remove : list of tuple
        List containing edges to be removed, represented as tuples of the form (node1, node2, edge key).
    """

    node, nei1, edge1_key = edge1
    node, nei2, edge2_key = edge2

    branches_to_remove = []
    if graph.degree(nei1)==1 and graph[node][nei1][edge1_key]['length']<length_threshold:
        # Identify the node with the smallest index, to ensure that edges are always represented
        # as (smallest index, largest index, key).
        if node>nei1:
            n1, n2 = nei1, node
        else:
            n1, n2 = node, nei1
        branches_to_remove.append((n1, n2, edge1_key))
    if graph.degree(nei2)==1 and graph[node][nei2][edge2_key]['length']<length_threshold:
        if node>nei2:
            n1, n2 = nei2, node
        else:
            n1, n2 = node, nei2
        branches_to_remove.append((n1, n2, edge2_key))

    return branches_to_remove

def handle_new_multiedge(graph, nei1, nei2, length_threshold, nodes_to_visit):
    """Auxiliary function for function `remove_degree_two_nodes`. This function is called when
    a node with degree two is removed from the graph but its neighbors already had a connection
    between them. In such a case, a new multiple edge is generated between the neighbors, and
    need to be handled.

    First, one of the edges is removed if its size is smaller than `length_threshold`. If an
    edge was removed, the degrees of the neighbors are checked. If a neighbor has degree 2, it
    means that it had degree 3 before the removal of the edge, and therefore it needs to be added
    to `nodes_to_visit`. If a neighbor has degree 1, it means that it had degree 2 and need to be
    removed from `nodes_to_visit`. Also, the remaining edge is now a branch.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    nei1 : hashable
        A node in the graph.
    nei2 : hashable
        Another node in the graph.
    length_threshold : float
        The threshold to decide if one of the multiple edges can be removed.
    nodes_to_visit : list of hashable
        Stack created in function `remove_degree_two_nodes` storing nodes with degree two to be processed.

    Returns
    -------
    is_branch : bool
        True if the multiedge became a branch after the function was executed.
    """

    was_removed = remove_small_mul(graph, nei1, nei2, 2*length_threshold)
    is_branch = False
    if was_removed:
        nei1_degree = graph.degree(nei1)
        if nei1_degree==2:
            nodes_to_visit.append(nei1)
        elif nei1_degree==1:
            remove_if_in_list(nodes_to_visit, nei1)         # This was not in the old algorithm
            is_branch = True
        nei2_degree = graph.degree(nei2)
        if nei2_degree==2:
            nodes_to_visit.append(nei2)
        elif nei2_degree==1:
            remove_if_in_list(nodes_to_visit, nei2)
            is_branch = True

    return is_branch

def remove_degree_two_nodes(graph, length_threshold, initial_node=None, return_branch_changes=False, verbose=False):
    """Remove nodes having degree two from the graph, connecting its respective neighbors.

    A node with degree two does not have topological significance in a graph representing
    terminations and bifurcations. Thus, it is assumed that they were generated by noise or
    segmentation and skeletonization problems.

    For example, suppose the following graph containing three nodes is to be analyzed:

    0 0 0 0 0 0 0 0 0 0 0 0
    0 1 2 0 0 0 0 0 0 0 1 0
    0 0 0 2 2 0 0 0 0 2 0 0
    0 0 0 0 0 2 1 2 2 0 0 0
    0 0 0 0 0 0 0 0 0 0 0 0

    where 1 indicate the position of a node and 2 a path between nodes. In this case, the node
    at the bottom is removed and the other two nodes are connected with a new edge representing
    a concatenation of the two previous edges and the position of the removed node:

    0 0 0 0 0 0 0 0 0 0 0 0
    0 1 2 0 0 0 0 0 0 0 1 0
    0 0 0 2 2 0 0 0 0 2 0 0
    0 0 0 0 0 2 2 2 2 0 0 0
    0 0 0 0 0 0 0 0 0 0 0 0

    Note that the removal of a node will generate multiple edges in the graph if the neighbors
    of the removed node are connected. Thus, there is a heuristic implemented in this function that
    assumes that such edges are often not desired. If one of these multiple edges is small, it
    is removed from the graph. Since the removal of an edge changes the degre of the nodes, new
    nodes with degree two might appear in the graph. Thus, the removal of degree two nodes needs to
    be done iteratively.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    length_threshold : float
        When a node is removed, if its neighbors are connected a multiple edge is created.
        If one of the multiple edges is smaller than `length_threshold`, it is removed from
        the graph.
    initial_node : hashable, optional
        If provided, instead of removing all nodes with degree two, `initial_node` is removed
        first. If new nodes with degree appear, they are also removed, and so on.
    return_branch_changes : bool, optional
        If True, the function returns all branches that were removed from the graph during
        the node removal process as well as branches that were added to the graph. This information
        is used in function `remove_branches` to update a priority queue.
    verbose : bool, optional
        If True, a message indicating the start of the process is printed.

    Returns
    -------
    added_branches : list of tuple
        List of edges that became branches in the removal provess. Each element of the list is a tuple
        of the form (node1, node2, edge key). Only returned if `return_branch_changes==True`.
    removed_branches : list of tuple
        List of edges that were branches in the graph but were removed. Each element of the list is a tuple
        of the form (node1, node2, edge key). Only returned if `return_branch_changes==True`.
    """

    pix_size = np.array(graph.graph['pix_size'])

    if verbose:
        print('\nRemoving degree two nodes...', end='')

    if return_branch_changes:
        removed_branches = set()
        added_branches = set()

    nodes_to_visit = []
    if initial_node is None:
        nodes_to_visit = list(degree_two_iter(graph, False, False))
    else:
        # Assumes node has degree two
        if degree_two_node_type(graph, initial_node)=='simple':
            # Node does not have self loop or multiple edges
            nodes_to_visit = [initial_node]

    while len(nodes_to_visit)>0:

        node = nodes_to_visit.pop()

        node_type = degree_two_node_type(graph, node)
        node_center = graph.nodes[node]['center']
        nei1, nei2, edge1_key, edge2_key = two_neighbors_data(graph, node, node_type)
        new_path, length_new_path = make_new_path(graph, (node, nei1, edge1_key), (node, nei2, edge2_key))

        has_nei_edge = False
        is_branch = False
        if node_type=='multiple':
            if graph.degree(nei1)==2:
                # After the removal of the edge, nei1 will not have degree 2
                nodes_to_visit.remove(nei1)
        else:
            if graph.has_edge(nei1, nei2):
                has_nei_edge = True
            else:
                if graph.degree(nei1)==1 or graph.degree(nei2)==1:
                    is_branch = True

        if is_branch and return_branch_changes:
            # Check if 'is_branch' attribute will need to be changed in priority queue
            b_to_rem = set(branches_to_remove(graph, (node, nei1, edge1_key),
                                              (node, nei2, edge2_key), length_threshold))
            for branch in b_to_rem:
                if branch in added_branches:
                    added_branches.remove(branch)
                else:
                    removed_branches.add(branch)

        graph.remove_edges_from([(node, nei1, edge1_key), (node, nei2, edge2_key)])
        graph.add_edge(nei1, nei2, **{'path':new_path, 'length':length_new_path, 'is_branch':is_branch})

        if has_nei_edge:
            # A new multiple edge was created
            is_branch = handle_new_multiedge(graph, nei1, nei2, length_threshold, nodes_to_visit)

        if is_branch:
            nei_edge_key = get_single_edge_key(graph, nei1, nei2)
            graph[nei1][nei2][nei_edge_key]['is_branch'] = True
            if return_branch_changes:
                if length_new_path<length_threshold:
                    added_branches.add((nei1, nei2, nei_edge_key))

    if return_branch_changes:
        return added_branches, removed_branches

def _remove_degree_two_nodes_old(graph, length_threshold, initial_node=None, verbose=False):
    """Remove nodes having degree two from the graph, connecting its respective neighbors.
    Old implementation, please use function `remove_degree_two_nodes_old` instead."""

    pix_size = np.array(graph.graph['pix_size'])

    if verbose:
        print('\nRemoving degree two nodes...', end='')

    nodes_to_visit = []
    if initial_node is None:
        nodes_to_visit = list(degree_two_iter(graph, False, False))
    else:
        # Assumes node has degree two
        if degree_two_node_type(graph, initial_node)=='simple':
            # Node does not have self loop or multiple edges
            nodes_to_visit = [initial_node]

    while len(nodes_to_visit)>0:

        node = nodes_to_visit.pop()

        node_type = degree_two_node_type(graph, node)
        node_center = graph.nodes[node]['center']
        neighbors = list(graph.neighbors(node))
        if node_type=='simple':
            nei1, nei2 = neighbors
            edge1_key = get_single_edge_key(graph, node, nei1)   # Cannot assume key is 0
            edge2_key = get_single_edge_key(graph, node, nei2)
        elif node_type=='multiple':
            nei1 = nei2 = neighbors[0]
            edge1_key, edge2_key = list(graph[node][nei1].keys())
        elif node_type=='loop':
            raise ValueError('Cannot process self-loop.')

        edge1_attrs = graph[node][nei1][edge1_key]
        edge2_attrs = graph[node][nei2][edge2_key]
        path_nei1 = edge1_attrs['path']
        path_nei2 = edge2_attrs['path']

        if node<nei1:
            # If node<nei1, path runs from node to nei1, we need to reverse that
            path_nei1 = path_nei1[::-1]
        if node>nei2:
            path_nei2 = path_nei2[::-1]

        new_path = path_nei1 + [node_center] + path_nei2
        if nei1>nei2:
            new_path = new_path[::-1]

        new_path_seg = np.array([path_nei1[-1], node_center, path_nei2[0]])
        length_new_seg = path_length(new_path_seg, pix_size)
        length_new_path = edge1_attrs['length'] + length_new_seg + edge2_attrs['length']

        has_nei_edge = False
        is_branch = False
        if node_type=='multiple':
            if graph.degree(nei1)==2:
                nodes_to_visit.remove(nei1)
        else:
            if graph.has_edge(nei1, nei2):
                has_nei_edge = True
            else:
                if graph.degree(nei1)==1 or graph.degree(nei2)==1:
                    is_branch = True

        graph.remove_edges_from([(node, nei1, edge1_key), (node, nei2, edge2_key)])
        graph.add_edge(nei1, nei2, **{'path':new_path, 'length':length_new_path, 'is_branch':is_branch})

        if has_nei_edge:
            was_removed = remove_small_mul(graph, nei1, nei2, 2*length_threshold)
            if was_removed:
                nei1_degree = graph.degree(nei1)
                if nei1_degree==2:
                    nodes_to_visit.append(nei1)
                elif nei1_degree==1:
                    remove_if_in_list(nodes_to_visit, nei1)         # This was not in the old algorithm
                    nei_edge_key = get_single_edge_key(graph, nei1, nei2)
                    graph[nei1][nei2][nei_edge_key]['is_branch'] = True
                nei2_degree = graph.degree(nei2)
                if nei2_degree==2:
                    nodes_to_visit.append(nei2)
                elif nei2_degree==1:
                    remove_if_in_list(nodes_to_visit, nei2)
                    nei_edge_key = get_single_edge_key(graph, nei1, nei2)
                    graph[nei1][nei2][nei_edge_key]['is_branch'] = True

def remove_branches(graph, length_threshold, verbose=False):
    """Remove graph edges associated with small branches. A branch edge is defined as an
    edge incident on at least one node with degree one (i.e., a termination).

    The branches are removed iteratively. This is so because the removal of a branch might
    lead to a node having degree two in the graph, which needs to be removed since it does
    not represent a termination or bifurcation. In turn, the removal of a node with degree
    two might lead to a new branch, which also needs to be removed, and so on.

    Note that the graph is modified in-place.

    Please see function `remove_degree_two_nodes` for a description regarding the removal
    of nodes with degree two.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    length_threshold : float
        Branches with size smaller than `length_threshold` are removed.
    verbose : bool, optional
        If True, the progress of the removal is printed.
    """

    pix_size = np.array(graph.graph['pix_size'])
    if verbose:
        print('\nRemoving branches...')
        num_branches_removed = 0

    # Create priority queue for all branches smaller than `length_threshold`
    branch_small_edges = list(filter(lambda edge: edge[3]['is_branch'] and edge[3]['length']<length_threshold,
                                     graph.edges(data=True, keys=True)))
    if len(branch_small_edges)==0:
        return

    branch_small_edges = map(lambda edge: (edge[3]['length'], (edge[0], edge[1], edge[2])), branch_small_edges)
    lengths, edges = zip(*branch_small_edges)
    branch_queue = util.PriorityQueue(lengths, edges)

    while branch_queue:

        if verbose:
            if num_branches_removed%10==0:
                print(f'\r{num_branches_removed} branches removed', end='')
            num_branches_removed += 1

        length_smal_edge, (node1, node2, key), _ = branch_queue.pop_task()
        graph.remove_edge(node1, node2, key)

        # Since an edge was removed, we need to check if an incident node now has degree 1 or 2
        if graph.degree(node1)==0:
            target_node = node2
        else:
            target_node = node1

        target_node_degree = graph.degree(target_node)
        if target_node_degree==2:
            added_branches, removed_branches = remove_degree_two_nodes(graph, length_threshold,
                                                                       target_node, return_branch_changes=True)
            for branch in added_branches:
                node1, node2, key = branch
                branch_queue.add_task(graph[node1][node2][key]['length'], branch)
            for branch in removed_branches:
                branch_queue.remove_task(branch)
        elif target_node_degree==1:
            target_neighbor = get_single_neighbor(graph, target_node)
            target_edge_key = get_single_edge_key(graph, target_node, target_neighbor)
            target_edge = graph[target_node][target_neighbor][target_edge_key]
            target_edge['is_branch'] = True
            branch_queue.add_task(target_edge['length'], (target_node, target_neighbor, target_edge_key))

def _remove_branches_old(graph, length_threshold, verbose=False):
    """Remove graph edges associated with small branches. A branch edge is defined as an
    edge incident on at least one node with degree one (i.e., a termination).
    Old implementation, please use function `remove_branches` instead.
    """

    pix_size = np.array(graph.graph['pix_size'])
    if verbose:
        print('\nRemoving branches...')
        num_branches_removed = 0

    branch_removed = True
    while branch_removed:

        if verbose:
            if num_branches_removed%10==0:
                print(f'\r{num_branches_removed} branches removed', end='')
            num_branches_removed += 1

        branch_edges = list(filter(lambda edge: edge[3], graph.edges(data='is_branch', keys=True)))
        if len(branch_edges)>0:
            lengths = [graph[edge[0]][edge[1]][edge[2]]['length'] for edge in branch_edges]
            ind_smal_edge = argmin(lengths)
            length_smal_edge = lengths[ind_smal_edge]
            if length_smal_edge<length_threshold:
                smallest_edge = branch_edges[ind_smal_edge]
                node1, node2, key, _ = smallest_edge
                graph.remove_edge(node1, node2, key)

                # Since an edge was removed, we need to check if a node now has degree 1 or 2
                if graph.degree(node1)==0:
                    target_node = node2
                else:
                    target_node = node1

                target_node_degree = graph.degree(target_node)
                if target_node_degree==2:
                    remove_degree_two_nodes(graph, length_threshold, target_node)
                elif target_node_degree==1:
                    target_neighbor = get_single_neighbor(graph, target_node)
                    target_edge_key = get_single_edge_key(graph, target_node, target_neighbor)
                    graph[target_node][target_neighbor][target_edge_key]['is_branch'] = True
            else:
                branch_removed = False
        else:
            branch_removed = False

def adjust_graph(graph, length_threshold, keep_nodes=False, collapse_indices=True, verbose=False):
    """Adjust the nodes and edges of a graph, using some heuristics to simplify its topology.
    The function does three main procedures:

    1. Removal of multiple edges between nodes as well as self-loops smaller than `length_threshold`.
    Please see function `remove_small_mul_all` for a description of the methodology.
    2. Removal of nodes with degree two, which should not be in a graph representing bifurcations
    and terminations. The 'path' attribute of the edges associated to degree two nodes are concatenated
    and associated to new edges between the neighbors of the removed nodes. Please refer to function
    `remove_degree_two_nodes` for a description of the procedure.
    3. Removal of branches smaller than `length_threshold`. A branch edge is defined as an edge incident
    on at least one node with degree one (i.e., a termination). Branches are removed iteratively, that is,
    after the removal of a branch, new branches might be created, those are also removed and so on.
    Please see function `remove_branches` for a description of the removal methodology.

    A new graph is returned.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The input graph.
    length_threshold : float
        Branches with size smaller than `length_threshold` are removed.
    keep_nodes : bool, optional
        If False, nodes having degree zero are removed. If True, the returned graph will have the
        same number of nodes as the input graph.
    collapse_indices : bool, optional
        If True and `keep_nodes==False`, nodes are relabeled with consecutive indices. For instance, if
        after the removal of some nodes the indices become [2, 5, 6, 8, 12], the new indices will be
        [0, 1, 2, 3, 4]. Note that if node labels in the input graph are not integers, they will become
        integers in the returned graph.
    verbose : bool, optional
        If True, the progress of the graph adjustment is printed.
    """

    new_graph = graph.copy()

    add_length(new_graph)
    add_branch_info(new_graph)

    remove_small_mul_all(new_graph, 2*length_threshold)
    remove_degree_two_nodes(new_graph, length_threshold, verbose=verbose)
    remove_branches(new_graph, length_threshold, verbose)
    remove_small_graph_components(new_graph, 2*length_threshold)

    if not keep_nodes:
        zero_degree_nodes = list(filter(lambda x: x[1]==0, dict(new_graph.degree()).items()))
        if len(zero_degree_nodes)>0:
            zero_degree_nodes = list(zip(*zero_degree_nodes))[0]
            new_graph.remove_nodes_from(zero_degree_nodes)

        if collapse_indices:
            new_graph = nx.convert_node_labels_to_integers(new_graph, ordering='default', label_attribute='old_id')

    return new_graph

if __name__=='__main__':

    # Networkx commands reference for Graph
    graph = nx.Graph()
    graph.add_nodes_from([(0, {'color':'blue'}), (1, {'color':'red'}), (2, {'color':'green'})])
    graph.add_edges_from([(0, 1, {'relation':'enemy'}), (0, 2, {'relation':'enemy'}), (1, 2, {'relation':'friend'})])

    print('Graph output')
    print(graph.adj)
    print(graph[0])                      # Dict neighbor:attrs
    print(graph[0][1])                   # Dict attrs
    print(graph.get_edge_data(0, 1))     # Same as above
    #print(graph[0, 1])                  # Error
    print(graph[0][1]['relation'])       # Edge attribute
    print(graph.nodes)                   # List of nodes
    print(graph.nodes[0])                # Dict attrs
    print(graph.nodes(data=True))        # Dict  attrs
    print(graph.nodes(data='color'))     # List (node_idx, attribute)
    print(graph.edges)                   # List of edges
    print(graph.edges(data=True))        # List of tuples (node1, node2, attrs)
    print(graph.edges(data='relation'))  # List of tuples (node1, node2, attribute)
    print(nx.get_edge_attributes(graph, 'relation'))  # Dict containing attribute values

    # Networkx commands reference for MultiGraph
    graph = nx.MultiGraph()
    graph.add_nodes_from([(0, {'color':'blue'}), (1, {'color':'red'}), (2, {'color':'green'})])
    keys = graph.add_edges_from([(0, 1, {'relation':'enemy'}), (0, 1, {'relation':'brothers'}),
                          (0, 2, {'relation':'enemy'}), (1, 2, {'relation':'friend'})])

    graph2 = nx.MultiGraph()
    graph2.add_nodes_from([(0, {'color':'blue'}), (1, {'color':'red'}), (2, {'color':'green'})])
    keys = graph2.add_edges_from([(0, 1, {'relation':'enemy'}), (0,1)])

    graph3 = nx.MultiGraph()
    graph3.add_nodes_from([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    keys = graph3.add_edges_from([(0, 1, {'length':6}), (0, 2, {'length':5}), (3, 4, {'length':2}), (4, 5, {'length':3}),
                                 (5, 6, {'length':1}), (7, 8, {'length':4}), (7, 8, {'length':4}), (8, 9, {'length':1})])

    print('\nMultiGraph output')
    print(keys)
    print(graph.adj)
    print(graph[0])                      # Dict neighbor:{edge_idx:attrs}
    print(graph[0][1])                   # Dict edge_idx:attrs
    print(graph.get_edge_data(0, 1))     # Same as above, can also use graph.get_edge_data(0, 1, key=edge_idx)
    #print(graph[0, 1])                  # Error
    print(graph[0][1][0]['relation'])    # Edge attribute
    print(graph.nodes)                   # List of nodes
    print(graph.nodes(data=True))        # Dict  attrs
    print(graph.nodes(data='color'))     # List (node_idx, attribute)
    print(graph.edges)                   # List of (node1, node2, edge_idx) tuples
    print(graph.edges(data=True))        # List of tuples (node1, node2, attrs) or list of tuples (node1, node2, edge_idx, attrs) if keys=True
    print(graph.edges(data='relation'))  # List of tuples (node1, node2, attribute) or list of tuples (node1, node2, edge_idx, attribute) if keys=True