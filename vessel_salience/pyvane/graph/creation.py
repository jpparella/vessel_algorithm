"""Module for creating a graph from a binary skeleton image."""

import numpy as np
from scipy import ndimage as ndi
import networkx as nx
from .. import util

class InterestPoint:
    """Class representing a termination or bifurcation point.

    A bifurcation can have more than one associated pixel. Therefore, the interest point
    is represented as a list of pixels and a center.

    Parameters
    ----------
    pixels_coords : list of tuple
        Coordinates of the pixels associated to the interest point.
    point_type : {'bifurcation', 'termination'}
        Type of the point.

    Attributes
    ----------
    pixels : list of tuple
        Coordinates of the pixels associated to the interest point.
    center : tuple
        Center point of the interest point.
    type : str
        Type of the interest point.
    ndim : int
        Number of coordinates of the point.
    branches : list of tuple
        Branches associated to the point. A branch is a pixel having two neighbors, one of which is the
        interest point. The list is initially empty. Method self.add_branches needs to be called for
        populating the variable.
    """

    point_code_to_name = {0:'bifurcation', 1:'termination'}
    point_name_to_code = {v:k for k, v in point_code_to_name.items()}

    def __init__(self, pixels_coords, point_type):

        center = np.mean(pixels_coords, axis=0)             # Calculate center
        center_int = tuple(np.round(center).astype(int))

        self.pixels = list(map(tuple, pixels_coords))       # Store as list of tuples
        self.center = center_int
        self.type = point_type
        self.ndim = len(center)
        self.branches = []

    def add_branches(self, img_num_neighbors):
        """Obtain branches (pixels with two neighbors) connected to an interest point.

        Parameters
        ----------
        img_num_neighbors : ndarray
            Each element of the array contain the number of neighbors of a pixel in some binary image.
            For instance, the center point of a cross has 4 neighbors.

        Returns
        -------
        branches : list of tuple
            The identified branches. The branches will also be added to self.branches.
        """

        if self.ndim != img_num_neighbors.ndim:
            raise ValueError(f'Dimension mismatch between interest point ({self.ndim}) and neighborhood image ({img_num_neighbors.ndim})')

        if len(self.branches)>0:
            return self.branches

        branches = set()
        for pixel in self.pixels:
            for neighbor in iterate_neighbors(pixel):
                if is_inside(neighbor, img_num_neighbors.shape):
                    if img_num_neighbors[neighbor]==2:
                        branches.add(neighbor)

        self.branches = list(map(tuple, branches))
        return branches

    @classmethod
    def map_point_type(cls, point_type, code_to_name=True):
        """Map point code to name, or vice-versa.

        Parameters
        ----------
        point_type : int
            Code of the point.
        code_to_name : bool
            If False, the function maps a point name to code.

        Returns
        -------
        Union[int, str]
            The point name or code.
        """

        if code_to_name:
            if point_type not in cls.point_code_to_name:
                raise ValueError('Point type code not recognized')
            return cls.point_code_to_name[point_type]
        else:
            if point_type not in cls.point_name_to_code:
                raise ValueError('Point type name not recognized')
            return cls.point_name_to_code(point_type)

class BranchMap:
    """Auxiliary map for keeping track of interest points associated to each branch pixel.

    Parameters
    ----------
    ips : list of InterestPoint
        Interest points whose branches will be mapped.
    """

    def __init__(self, ips):

        branch_map = {}
        for ip_idx, ip in enumerate(ips):
            for branch in ip.branches:
                if branch in branch_map:
                    branch_map[branch].add(ip_idx)
                else:
                    branch_map[branch] = set([ip_idx])

        self.branch_map = branch_map

    def get_ip_ids(self, branch):
        """Given a branch pixel, returns the indices of the interest points associated to the branch.
        Usually, a list containing a single index is returned, but on some corner cases two values
        may be returned.

        Parameters
        ----------
        branch : tuple of int
            The coordinates of the branch.

        Returns
        -------
        list of int
            The indices of the interest points associated to the branch.
        """

        return list(self.branch_map[branch])


def is_inside(pixel_coord, img_shape):
    """Check if pixel is inside image.

    Parameters
    ----------
    pixel_coord : tuple of int
        Pixel to check.
    img_shape : tuple of int
        Size of the image.

    Returns
    -------
    is_inside : bool
        True if pixel is inside the image or False otherwise.
    """

    is_inside = (pixel_coord[0]>=0) and (pixel_coord[1]>=0) and (pixel_coord[0]<img_shape[0]) and (pixel_coord[1]<img_shape[1])
    if len(img_shape)==3:
        is_inside = is_inside and (pixel_coord[2]>=0) and (pixel_coord[2]<img_shape[2])

    return is_inside

def iterate_neighbors(pixel_coords):
    """Iterate over neighbors of a given pixel. Works for 2D and 3D images.

    Parameters
    ----------
    pixel_coord : tuple of int
        Reference pixel.

    Yields
    -------
    tuple of int
        The neighbors of the pixel.
    """

    if len(pixel_coords)==2:

        neis = [(pixel_coords[0]-1, pixel_coords[1]-1), (pixel_coords[0]-1, pixel_coords[1]),
                (pixel_coords[0]-1, pixel_coords[1]+1), (pixel_coords[0], pixel_coords[1]-1),
                (pixel_coords[0], pixel_coords[1]+1), (pixel_coords[0]+1, pixel_coords[1]-1),
                (pixel_coords[0]+1, pixel_coords[1]), (pixel_coords[0]+1, pixel_coords[1]+1)]

    elif len(pixel_coords)==3:

        neis = [(pixel_coords[0]-1, pixel_coords[1]-1, pixel_coords[2]-1), (pixel_coords[0]-1, pixel_coords[1]-1, pixel_coords[2]  ),
                (pixel_coords[0]-1, pixel_coords[1]-1, pixel_coords[2]+1), (pixel_coords[0]-1, pixel_coords[1]  , pixel_coords[2]-1),
                (pixel_coords[0]-1, pixel_coords[1]  , pixel_coords[2]  ), (pixel_coords[0]-1, pixel_coords[1]  , pixel_coords[2]+1),
                (pixel_coords[0]-1, pixel_coords[1]+1, pixel_coords[2]-1), (pixel_coords[0]-1, pixel_coords[1]+1, pixel_coords[2]  ),
                (pixel_coords[0]-1, pixel_coords[1]+1, pixel_coords[2]+1),
                (pixel_coords[0]  , pixel_coords[1]-1, pixel_coords[2]-1), (pixel_coords[0]  , pixel_coords[1]-1, pixel_coords[2]  ),
                (pixel_coords[0]  , pixel_coords[1]-1, pixel_coords[2]+1), (pixel_coords[0]  , pixel_coords[1]  , pixel_coords[2]-1),
                                                                           (pixel_coords[0]  , pixel_coords[1]  , pixel_coords[2]+1),
                (pixel_coords[0]  , pixel_coords[1]+1, pixel_coords[2]-1), (pixel_coords[0]  , pixel_coords[1]+1, pixel_coords[2]  ),
                (pixel_coords[0]  , pixel_coords[1]+1, pixel_coords[2]+1),
                (pixel_coords[0]+1, pixel_coords[1]-1, pixel_coords[2]-1), (pixel_coords[0]+1, pixel_coords[1]-1, pixel_coords[2]  ),
                (pixel_coords[0]+1, pixel_coords[1]-1, pixel_coords[2]+1), (pixel_coords[0]+1, pixel_coords[1]  , pixel_coords[2]-1),
                (pixel_coords[0]+1, pixel_coords[1]  , pixel_coords[2]  ), (pixel_coords[0]+1, pixel_coords[1]  , pixel_coords[2]+1),
                (pixel_coords[0]+1, pixel_coords[1]+1, pixel_coords[2]-1), (pixel_coords[0]+1, pixel_coords[1]+1, pixel_coords[2]  ),
                (pixel_coords[0]+1, pixel_coords[1]+1, pixel_coords[2]+1)
               ]

    for n in neis:
        yield n

def find_interest_points_type(img_comps, point_type_name, structure, verbose=False):
    """Identifies interest points (terminations or bifurcations) on a binary image. See function
    `find_interest_points` for details.

    Parameters
    ----------
    img_comps : ndarray
        Binary image.
    point_type_name : {'bifurcation', 'termination'}
        Type of the point to search.
    structure : ndarray
        Structuring element to use for detecting connected components
    verbose : bool
        If True, the progress of the search process is printed.

    Returns
    -------
    interest_points : list of InterestPoint
        Interest points found.
    """

    img_label, num_comps = ndi.label(img_comps, structure)   # Connected components
    components = ndi.find_objects(img_label)
    if verbose:
        num_components = len(components)
        print_interv = util.get_print_interval(num_components)
    interest_points = []
    for idx, component in enumerate(components):
        if verbose:
            if idx%print_interv==0 or idx==num_components-1:
                print(f'\rProcessing point {idx+1} of {num_components}...', end='')

        # Get coordinate of pixels inside region and transform to image (global) coordinates
        coords = np.nonzero(img_label[component]==idx+1)
        global_coords = []
        for idx, coord_axis in enumerate(coords):
            global_coords.append(coord_axis + component[idx].start)
        global_coords = list(zip(*global_coords))
        ip = InterestPoint(global_coords, InterestPoint.point_name_to_code[point_type_name])
        interest_points.append(ip)

    return interest_points

def find_interest_points(img_num_neighbors, verbose=False):
    """Identifies interest points (terminations and bifurcations) on a binary image. Input `img_num_neighbors`
    is an array containing the number of neighbors of each pixel.

    Parameters
    ----------
    img_num_neighbors : ndarray
        Each element of the array contains the number of neighbors of a pixel in some binary image.
        For instance, the center point of a cross has 4 neighbors.
    verbose : bool
        If True, the progress of the search process is printed.

    Returns
    -------
    interest_points : list of InterestPoint
        Interest points found.
    """

    structure = np.ones(img_num_neighbors.ndim*[3])

    # Bifurcations
    if verbose:
        print('Detecting bifurcations...')
    img_comps = img_num_neighbors >= 3
    ip_bif = find_interest_points_type(img_comps, 'bifurcation', structure, verbose)

    # Terminations
    if verbose:
        print('\nDetecting terminations...')
    img_comps = img_num_neighbors == 1
    ip_term = find_interest_points_type(img_comps, 'termination', structure, verbose)

    interest_points = ip_bif + ip_term

    return interest_points

def add_branches_to_ips(ips, img_num_neighbors, verbose=False):
    """Add branch information to all interest points in `ips`. The points are modified in place.

    Parameters
    ----------
    ips : list of InterestPoint
        Interest points.
    img_num_neighbors : ndarray
        Each element of the array contains the number of neighbors of a pixel in some binary image.
        For instance, the center point of a cross has 4 neighbors.
    verbose : bool
        If True, the progress is printed.
    """

    if verbose:
        print('\nAdding branches...')
    if verbose:
        num_points = len(ips)
        print_interv = util.get_print_interval(num_points)
    for idx, ip in enumerate(ips):
        if verbose:
            if idx%print_interv==0 or idx==num_points-1:
                print(f'\rProcessing point {idx+1} of {num_points}...', end='')
        ip.add_branches(img_num_neighbors)

def track_branch(interest_point, branch_index, img_num_neighbors):
    '''Track a given branch starting at a bifurcation or termination, stopping when finding
    another termination or bifurcation.  `branch_index` sets the branch to track (0, 1, 2, etc).
    `img_num_neighbors` contains the number of neighbors for each pixel.

    Parameters
    ----------
    interest_point : InterestPoint
        Starting point of the tracking process.
    branch_index : int
        Index of the branch to track.
    img_num_neighbors : ndarray
        Each element of the array contains the number of neighbors of a pixel in some binary image.
        For instance, the center point of a cross has 4 neighbors.

    Returns
    -------
    path : list of tuple
        Pixels between two interest points. All pixels in `path` have two neighbors. The first pixel
        is a branch of `interest_point` and the last pixel is a branch of some other interest point.
    '''

    if len(interest_point.branches)<=branch_index:
        print('Warning! There is no branch with the given index')
        return []

    first_point = interest_point.branches[branch_index]
    second_point = None
    for neighbor in iterate_neighbors(first_point):
        if img_num_neighbors[neighbor]==2:
            second_point = neighbor

    path = [first_point]
    if second_point is not None:     # If None, path has only one point
        path.append(second_point)
        prev_point = first_point
        curr_point = second_point
        found_neighbor = True
        while found_neighbor:        # While there is a neighbor with value 2 in img_num_neighbors
            found_neighbor = False
            for neighbor in iterate_neighbors(curr_point):
                if (img_num_neighbors[neighbor]==2) and (neighbor!=prev_point):
                    # If neighbor is found, add to path and update current and previous points
                    path.append(neighbor)
                    prev_point = curr_point
                    curr_point = neighbor
                    found_neighbor = True
                    break

    return path

def find_path_ip(path, ips):
    '''For a given path, find the interest point that is a neighbor of the last point in the path.

    Parameters
    ----------
    path : list of tuple
        Pixels returned by function `track_branch`.
    ips : list of InterestPoint
        Interest points to search.

    Returns
    -------
    idx : int
        Index of the interest point sought.
    '''

    last_path_point = path[-1]
    for idx, ip in enumerate(ips):
        if last_path_point in ip.branches:
            return idx

def track_branches(ips, img_num_neighbors, verbose=False):
    '''Track branches of interest points in `ips`. For a given branch of an interest point, the tracking starts
    at the branch and stops when finding another interest point. The process is repeated for all branches of all
    interest points.

    Parameters
    ----------
    ips : InterestPoint
        Interesting points to track.
    img_num_neighbors : ndarray
        Each element of the array contains the number of neighbors of a pixel in some binary image.
        For instance, the center point of a cross has 4 neighbors.
    verbose : bool
        If True, the progress is printed.

    Returns
    -------
    edges : list of tuple
        Paths tracked. Each element of the list is a tuple of the form (ip1_idx, ip2_idx, path), where ip1_idx
        and ip2_idx are the indices of the interest points and path a list of pixels between the two points.
    '''

    if verbose:
        print('\nTracking branches...')

    branch_map = BranchMap(ips)
    if verbose:
        num_points = len(ips)
        print_interv = util.get_print_interval(num_points)
    visited_branches = set()
    edges = []
    for ip1_idx, ip in enumerate(ips):
        if verbose:
            if ip1_idx%print_interv==0 or ip1_idx==num_points-1:
                print(f'\rProcessing point {ip1_idx+1} of {num_points}...', end='')

        for branch_idx, branch in enumerate(ip.branches):
            if branch not in visited_branches:
                path = track_branch(ip, branch_idx, img_num_neighbors)
                visited_branches.add(branch)
                visited_branches.add(path[-1])
                ip2_idx = branch_map.get_ip_ids(path[-1])
                if len(ip2_idx)==2:
                    # If branch is a single point between two bifurcations
                    if ip2_idx[0]==ip1_idx:
                        ip2_idx = ip2_idx[1]
                    else:
                        ip2_idx = ip2_idx[0]
                else:
                    ip2_idx = ip2_idx[0]

                edges.append((ip1_idx, ip2_idx, path))

    return edges

def unpad_coords(ips, edges):
    """Subtract 1 from the coordinates of all interest points and edges. Used when the
    original image is padded for avoiding indices outside the image. The procedure is done
    in place.

    Parameters
    ----------
    ips : list of InterestPoint
        List of interest points.
    edges : list of tuple
        Edges returned by function `track_branches`.
    """

    sub_1 = lambda x:x-1

    #list(map(tuple, pixels_coords))
    for ip in ips:
        ip.pixels = [tuple(map(sub_1, pixel)) for pixel in ip.pixels]
        ip.center = tuple(map(sub_1, ip.center))
        ip.branches = [tuple(map(sub_1, branch)) for branch in ip.branches]

    for edge in edges:
        path = edge[2]
        path[:] = [tuple(map(sub_1, pixel)) for pixel in path]

def remove_isolated_points(ips, edges):
    """Remove points that have no edge. When doing so, the list of `edges` needs to be updated
    since the indices of the point changed.

    Parameters
    ----------
    ips : list of InterestPoint
        List of interest points.
    edges : list of tuple
        Edges returned by function `track_branches`.

    Returns
    ----------
    new_ips : list of InterestPoint
        New list of interest points.
    new_edges : list of tuple
        Updated list of edges.
    """

    ips_indices = list(range(len(ips)))

    nodes = set([edge[0] for edge in edges] + [edge[1] for edge in edges])
    nodes_to_remove = set(set(ips_indices) - nodes)
    new_idx = 0
    idx_remap = dict(zip(ips_indices, [-1]*len(ips)))  # Will store indices remap
    for idx in range(len(ips)):
        if idx in nodes_to_remove:
            idx_remap[idx] = -1
        else:
            idx_remap[idx] = new_idx
            new_idx += 1

    new_ips = []
    for node in nodes:
        new_ips.append(ips[node])

    new_edges = []
    for edge in edges:
        new_edges.append((idx_remap[edge[0]], idx_remap[edge[1]], edge[2]))

    return new_ips, new_edges

def remove_single_pixel_self_edges(edges):
    """Remove corner case edges representing a single segment pixel between the same point, that is,
    a self-loop with one pixel.

    Parameters
    ----------
    edges : list of tuple
        Edges, same format as returned by function `track_branches`.

    Returns
    -------
    new_edges : list of tuple
        Updated edges.
    """

    new_edges = []
    for edge in edges:
        if edge[0]!=edge[1]:
            new_edges.append(edge)
        else:
            if len(edge[2])>1:
                new_edges.append(edge)

    return new_edges

def to_networkx(ips, edges, graph_attrs=None):
    """Converts list of interest points and edges to a networkx MultiGraph.

    Parameters
    ----------
    ips : list of InterestPoint
        List of interest points.
    edges : list of tuple
        Segments between interest points. Each element of the list is a tuple of the form
        (ip1_idx, ip2_idx, path), where ip1_idx and ip2_idx are the indices of the interest points
        and path a list of pixels between the two points.
    graph_attrs : dict
        Graph attributes added to the networkx graph (accessed as graph.graph).

    Returns
    -------
    graph : networkx.MultiGraph
        Graph representing the interest points and their connections.
    """

    if graph_attrs is None:
        graph_attrs = {}

    graph = nx.MultiGraph()
    for ip_idx, ip in enumerate(ips):
        ip_dict = {'pixels':ip.pixels, 'center':ip.center, 'type':ip.type, 'ndim':ip.ndim, 'branches':ip.branches}
        graph.add_node(ip_idx, **ip_dict)

    for edge in edges:
        edge_dict = {'path':edge[2]}
        graph.add_edge(edge[0], edge[1], **edge_dict)

    graph.graph = graph_attrs

    return graph

def create_graph(img_skel, verbose=False):
    """Generate graph from an image containing a skeleton.

    In the final graph, nodes represent bifurcations and terminations and edges indicate that there is
    a sequence of connected pixels between two nodes. Terminations are defined as skeleton points having
    only one adjacent pixel of the same color. Bifurcations are defined as skeleton `regions` composed of
    pixels having three or more neighbors.

    Nodes in the final graph have the following attributes:

    * 'pixels': list of pixels associated to the node. It is a single pixel for termination node.
    * 'center': pixel representing the center of the node. Identical to 'pixels' for terminations.
    * 'type': either 'bifurcation' or 'termination'.
    * 'ndim': number of coordinates of pixels associated to the node, that is, the dimension of the original image.
    * 'branches': list of pixels that are branches of a node. Branches are pixels having two neighbors, one
    of which is a pixel belonging to the node.

    Edges in the final graph have the following attributes:

    * 'path': list of pixels associated to the edge. Each pixel has exactly two neighbors in `img_skel`.

    Parameters
    ----------
    img_skel : Image
        Binary image containing the skeleton to process. Must contain only values 0 and 1.
    verbose : bool
        If True, prints the progress of the algorithm.

    Returns
    -------
    graph : networkx.MultiGraph
        Graph representing the skeleton. Note that the graph may have self-loops and multiple edges.
    """

    if tuple(img_skel.unique()) != (0, 1):
        raise ValueError('Image must only have values 0 and 1')

    img_skel_data = img_skel.data

    if img_skel_data.dtype != np.uint8:
        img_skel_data = img_skel_data.astype(np.uint8)

    img_skel_data_pad = np.pad(img_skel_data, 1)

    if img_skel.ndim==2:
        structue = np.ones((3, 3), dtype=np.uint8)
    elif img_skel.ndim==3:
        structue = np.ones((3, 3, 3), dtype=np.uint8)

    img_skel_data_pad = util.remove_small_comp(img_skel_data_pad, 2, structure=structue)

    # img_num_neighbors stores the number of neighbors of each pixel. Value -1 is assigned to background pixels
    img_skel_data_pad = img_skel_data_pad.astype(np.int8)
    img_num_neighbors = ndi.correlate(img_skel_data_pad, structue)
    img_num_neighbors = img_num_neighbors*img_skel_data_pad - 1

    # Find interest points
    ips = find_interest_points(img_num_neighbors, verbose)
    # Add branches to each point
    add_branches_to_ips(ips, img_num_neighbors, verbose)

    edges = track_branches(ips, img_num_neighbors, verbose)

    ips, edges = remove_isolated_points(ips, edges)
    edges = remove_single_pixel_self_edges(edges)
    unpad_coords(ips, edges)

    graph_attrs = {'path':img_skel.path, 'pix_size':img_skel.pix_size, 'ndim':img_skel.ndim,
                   'shape':img_skel.shape, 'or_vmax':img_skel.or_vmax, 'or_vmin':img_skel.or_vmin}
    graph = to_networkx(ips, edges, graph_attrs)

    return graph