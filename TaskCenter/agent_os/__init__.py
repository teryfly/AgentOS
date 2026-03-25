"""
Agent OS namespace package.

This is a PEP 420 namespace package, allowing multiple
independent packages under the agent_os namespace.
"""
# This file intentionally left minimal to support namespace packages
__path__ = __import__('pkgutil').extend_path(__path__, __name__)