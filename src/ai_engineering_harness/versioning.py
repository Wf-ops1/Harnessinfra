"""Version namespaces for the installed package and serialized contracts."""

from importlib.metadata import version

DISTRIBUTION_NAME = "ai-engineering-harness"

# Package metadata is authored once in pyproject.toml and read from the installation.
PACKAGE_VERSION = version(DISTRIBUTION_NAME)

# Schema versions evolve independently from the package and definition versions.
GRAPH_SCHEMA_VERSION = "1.0"
ARTIFACT_SCHEMA_VERSION = "2.0"
POLICY_SCHEMA_VERSION = "1.0"
