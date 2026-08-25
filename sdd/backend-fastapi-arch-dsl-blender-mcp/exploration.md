## Exploration: backend-fastapi-arch-dsl-blender-mcp

### Current State
The `sketchos` project currently appears to be a C/C++ centric application with `src/boot` and `src/kernel` directories. There is an existing `blender-mcp/` directory which functions as a Blender add-on. This add-on includes a Python-based Model Context Protocol (MCP) server (`blender-mcp/src/blender_mcp/server.py`) using `FastMCP`. This Blender MCP server exposes various tools for interacting with Blender, including executing arbitrary Python code (`execute_blender_code`), getting scene information, and managing assets from sources like Polyhaven and Sketchfab.

### Affected Areas
-   `blender-mcp/src/blender_mcp/server.py` — This existing MCP server will be the client to our new SketchOS backend. Its `execute_blender_code` tool will be heavily utilized by the new backend to manipulate Blender based on architectural definitions.
-   `./` (root of SketchOS project) — A new directory (e.g., `backend/` or `sketchos_backend/`) will be created for the FastAPI/FastMCP application and the `arch_dsl.py`.

### Approaches
1.  **Standalone FastAPI/FastMCP Backend with Pydantic DSL (Recommended)**
    *   **Brief Description:** Create a new Python project for the SketchOS backend. This backend will be a `FastMCP` server itself, exposing its own set of tools/APIs for SketchOS functionalities. It will define the Architectural DSL using Pydantic models in `arch_dsl.py`. This backend will act as a client to the existing `blender-mcp` server, sending commands (potentially Python code generated from the DSL) to manipulate Blender.
    *   **Pros:**
        *   Clean separation of concerns: The core SketchOS logic resides in its own backend, decoupled from Blender's internals.
        *   Leverages existing `FastMCP` in `blender-mcp`: The new backend can easily interact with Blender's exposed functionalities.
        *   Pydantic provides strong data validation and serialization for architectural definitions.
        *   Scalable: The backend can be deployed independently.
    *   **Cons:**
        *   Requires setting up a new Python environment and project structure.
        *   Communication between two MCP servers (SketchOS backend as client to Blender MCP server) adds a layer of complexity.
    *   **Effort:** Medium

### Recommendation
I recommend the **Standalone FastAPI/FastMCP Backend with Pydantic DSL** approach. This provides a robust, scalable, and modular architecture. The existing `blender-mcp` server's capabilities, especially the `execute_blender_code` tool, are perfectly suited for this integration. The new SketchOS backend will manage the architectural definitions using Pydantic, and then translate these into Blender commands via the `blender-mcp`'s MCP server.

### Risks
-   **Complexity of two-way communication:** While the SketchOS backend will primarily *send* commands to Blender, there might be a need for Blender to *send back* information. This could introduce complexities in managing bidirectional communication.
-   **Performance overhead:** Serializing Pydantic models to JSON, sending them over a socket, then potentially generating and executing Python code in Blender might introduce performance overhead for very complex architectural models.
-   **Blender API limitations:** Relying on `execute_blender_code` means we're constrained by what's possible directly via Blender's Python API.
-   **Version compatibility:** Ensuring compatibility between the new backend's Python environment and the Blender add-on's Python environment.

### Ready for Proposal
Yes. The orchestrator should now proceed to the proposal phase, detailing the chosen approach and outlining the initial structure for the new backend and the `arch_dsl.py` file.
