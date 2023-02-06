from .test_nodes import ListPassThroughInvocation, PromptTestInvocation
from ldm.invoke.app.services.graph_execution_state import Graph, GraphInvocation, InvalidEdgeError, NodeAlreadyInGraphError, NodeNotFoundError, are_connections_compatible, EdgeConnection, CollectInvocation, IterateInvocation
from ldm.invoke.app.invocations.generate import ImageToImageInvocation, TextToImageInvocation
from ldm.invoke.app.invocations.upscale import UpscaleInvocation
import pytest


# Helpers
def create_edge(from_id: str, from_field: str, to_id: str, to_field: str) -> tuple[EdgeConnection, EdgeConnection]:
    return (EdgeConnection(node_id = from_id, field = from_field), EdgeConnection(node_id = to_id, field = to_field))

# Tests

def test_connections_are_compatible():
    from_node = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    from_field = "image"
    to_node = UpscaleInvocation(id = "2")
    to_field = "image"

    result = are_connections_compatible(from_node, from_field, to_node, to_field)

    assert result == True

def test_connections_are_incompatible():
    from_node = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    from_field = "image"
    to_node = UpscaleInvocation(id = "2")
    to_field = "strength"

    result = are_connections_compatible(from_node, from_field, to_node, to_field)

    assert result == False

def test_connections_incompatible_with_invalid_fields():
    from_node = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    from_field = "invalid_field"
    to_node = UpscaleInvocation(id = "2")
    to_field = "image"

    # From field is invalid
    result = are_connections_compatible(from_node, from_field, to_node, to_field)
    assert result == False

    # To field is invalid
    from_field = "image"
    to_field = "invalid_field"

    result = are_connections_compatible(from_node, from_field, to_node, to_field)
    assert result == False

def test_graph_can_add_node():
    g = Graph()
    n = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    g.add_node(n)

    assert n.id in g.nodes

def test_graph_fails_to_add_node_with_duplicate_id():
    g = Graph()
    n = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    g.add_node(n)
    n2 = TextToImageInvocation(id = "1", prompt = "Banana sushi the second")

    with pytest.raises(NodeAlreadyInGraphError):
        g.add_node(n2)

def test_graph_adds_edge():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    g.add_node(n1)
    g.add_node(n2)
    e = create_edge(n1.id,"image",n2.id,"image")

    g.add_edge(e)

    assert e in g.edges

def test_graph_fails_to_add_edge_with_cycle():
    g = Graph()
    n1 = UpscaleInvocation(id = "1")
    g.add_node(n1)
    e = create_edge(n1.id,"image",n1.id,"image")
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e)

def test_graph_fails_to_add_edge_with_long_cycle():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    n3 = UpscaleInvocation(id = "3")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    e1 = create_edge(n1.id,"image",n2.id,"image")
    e2 = create_edge(n2.id,"image",n3.id,"image")
    e3 = create_edge(n3.id,"image",n2.id,"image")
    g.add_edge(e1)
    g.add_edge(e2)
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e3)

def test_graph_fails_to_add_edge_with_missing_node_id():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    g.add_node(n1)
    g.add_node(n2)
    e1 = create_edge("1","image","3","image")
    e2 = create_edge("3","image","1","image")
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e1)
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e2)

def test_graph_fails_to_add_edge_when_destination_exists():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    n3 = UpscaleInvocation(id = "3")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    e1 = create_edge(n1.id,"image",n2.id,"image")
    e2 = create_edge(n1.id,"image",n3.id,"image")
    e3 = create_edge(n2.id,"image",n3.id,"image")
    g.add_edge(e1)
    g.add_edge(e2)
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e3)


def test_graph_fails_to_add_edge_with_mismatched_types():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    g.add_node(n1)
    g.add_node(n2)
    e1 = create_edge("1","image","2","strength")
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e1)

def test_graph_connects_collector():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = TextToImageInvocation(id = "2", prompt = "Banana sushi 2")
    n3 = CollectInvocation(id = "3")
    n4 = ListPassThroughInvocation(id = "4")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_node(n4)

    e1 = create_edge("1","image","3","item")
    e2 = create_edge("2","image","3","item")
    e3 = create_edge("3","collection","4","collection")
    g.add_edge(e1)
    g.add_edge(e2)
    g.add_edge(e3)

# TODO: test that derived types mixed with base types are compatible

def test_graph_collector_invalid_with_varying_input_types():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = PromptTestInvocation(id = "2", prompt = "banana sushi 2")
    n3 = CollectInvocation(id = "3")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    e1 = create_edge("1","image","3","item")
    e2 = create_edge("2","prompt","3","item")
    g.add_edge(e1)
    
    with pytest.raises(InvalidEdgeError):
        g.add_edge(e2)

def test_graph_collector_invalid_with_varying_input_output():
    g = Graph()
    n1 = PromptTestInvocation(id = "1", prompt = "Banana sushi")
    n2 = PromptTestInvocation(id = "2", prompt = "Banana sushi 2")
    n3 = CollectInvocation(id = "3")
    n4 = ListPassThroughInvocation(id = "4")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_node(n4)

    e1 = create_edge("1","prompt","3","item")
    e2 = create_edge("2","prompt","3","item")
    e3 = create_edge("3","collection","4","collection")
    g.add_edge(e1)
    g.add_edge(e2)

    with pytest.raises(InvalidEdgeError):
        g.add_edge(e3)

def test_graph_collector_invalid_with_non_list_output():
    g = Graph()
    n1 = PromptTestInvocation(id = "1", prompt = "Banana sushi")
    n2 = PromptTestInvocation(id = "2", prompt = "Banana sushi 2")
    n3 = CollectInvocation(id = "3")
    n4 = PromptTestInvocation(id = "4")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_node(n4)

    e1 = create_edge("1","prompt","3","item")
    e2 = create_edge("2","prompt","3","item")
    e3 = create_edge("3","collection","4","prompt")
    g.add_edge(e1)
    g.add_edge(e2)

    with pytest.raises(InvalidEdgeError):
        g.add_edge(e3)

def test_graph_connects_iterator():
    g = Graph()
    n1 = ListPassThroughInvocation(id = "1")
    n2 = IterateInvocation(id = "2")
    n3 = ImageToImageInvocation(id = "3", prompt = "Banana sushi")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    e1 = create_edge("1","collection","2","collection")
    e2 = create_edge("2","item","3","image")
    g.add_edge(e1)
    g.add_edge(e2)

# TODO: TEST INVALID ITERATOR SCENARIOS

def test_graph_iterator_invalid_if_multiple_inputs():
    g = Graph()
    n1 = ListPassThroughInvocation(id = "1")
    n2 = IterateInvocation(id = "2")
    n3 = ImageToImageInvocation(id = "3", prompt = "Banana sushi")
    n4 = ListPassThroughInvocation(id = "4")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_node(n4)

    e1 = create_edge("1","collection","2","collection")
    e2 = create_edge("2","item","3","image")
    e3 = create_edge("4","collection","2","collection")
    g.add_edge(e1)
    g.add_edge(e2)

    with pytest.raises(InvalidEdgeError):
        g.add_edge(e3)

def test_graph_iterator_invalid_if_input_not_list():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", promopt = "Banana sushi")
    n2 = IterateInvocation(id = "2")
    g.add_node(n1)
    g.add_node(n2)

    e1 = create_edge("1","collection","2","collection")

    with pytest.raises(InvalidEdgeError):
        g.add_edge(e1)

def test_graph_iterator_invalid_if_output_and_input_types_different():
    g = Graph()
    n1 = ListPassThroughInvocation(id = "1")
    n2 = IterateInvocation(id = "2")
    n3 = PromptTestInvocation(id = "3", prompt = "Banana sushi")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    e1 = create_edge("1","collection","2","collection")
    e2 = create_edge("2","item","3","prompt")
    g.add_edge(e1)

    with pytest.raises(InvalidEdgeError):
        g.add_edge(e2)

def test_graph_validates():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    g.add_node(n1)
    g.add_node(n2)
    e1 = create_edge("1","image","2","image")
    g.add_edge(e1)

    assert g.is_valid() == True

def test_graph_invalid_if_edges_reference_missing_nodes():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    g.nodes[n1.id] = n1
    e1 = create_edge("1","image","2","image")
    g.edges.add(e1)

    assert g.is_valid() == False

def test_graph_invalid_if_subgraph_invalid():
    g = Graph()
    n1 = GraphInvocation(id = "1")
    n1.graph = Graph()

    n1_1 = TextToImageInvocation(id = "2", prompt = "Banana sushi")
    n1.graph.nodes[n1_1.id] = n1_1
    e1 = create_edge("1","image","2","image")
    n1.graph.edges.add(e1)

    g.nodes[n1.id] = n1

    assert g.is_valid() == False

def test_graph_invalid_if_has_cycle():
    g = Graph()
    n1 = UpscaleInvocation(id = "1")
    n2 = UpscaleInvocation(id = "2")
    g.nodes[n1.id] = n1
    g.nodes[n2.id] = n2
    e1 = create_edge("1","image","2","image")
    e2 = create_edge("2","image","1","image")
    g.edges.add(e1)
    g.edges.add(e2)

    assert g.is_valid() == False

def test_graph_invalid_with_invalid_connection():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    g.nodes[n1.id] = n1
    g.nodes[n2.id] = n2
    e1 = create_edge("1","image","2","strength")
    g.edges.add(e1)

    assert g.is_valid() == False


# TODO: Subgraph operations
def test_graph_gets_subgraph_node():
    g = Graph()
    n1 = GraphInvocation(id = "1")
    n1.graph = Graph()
    n1.graph.add_node

    n1_1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n1.graph.add_node(n1_1)

    g.add_node(n1)

    result = g.get_node('1.1')

    assert result is not None
    assert result.id == '1'
    assert result == n1_1

def test_graph_fails_to_get_missing_subgraph_node():
    g = Graph()
    n1 = GraphInvocation(id = "1")
    n1.graph = Graph()
    n1.graph.add_node

    n1_1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n1.graph.add_node(n1_1)

    g.add_node(n1)

    with pytest.raises(NodeNotFoundError):
        result = g.get_node('1.2')

def test_graph_fails_to_enumerate_non_subgraph_node():
    g = Graph()
    n1 = GraphInvocation(id = "1")
    n1.graph = Graph()
    n1.graph.add_node

    n1_1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n1.graph.add_node(n1_1)

    g.add_node(n1)
    
    n2 = UpscaleInvocation(id = "2")
    g.add_node(n2)

    with pytest.raises(NodeNotFoundError):
        result = g.get_node('2.1')

def test_graph_gets_networkx_graph():
    g = Graph()
    n1 = TextToImageInvocation(id = "1", prompt = "Banana sushi")
    n2 = UpscaleInvocation(id = "2")
    g.add_node(n1)
    g.add_node(n2)
    e = create_edge(n1.id,"image",n2.id,"image")
    g.add_edge(e)

    nxg = g.nx_graph()

    assert '1' in nxg.nodes
    assert '2' in nxg.nodes
    assert ('1','2') in nxg.edges


# TODO: Graph serializes and deserializes