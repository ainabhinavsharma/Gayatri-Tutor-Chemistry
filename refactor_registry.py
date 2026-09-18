import re

with open('core/agents/registry.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace register()
new_register = '''    def register(self, spec: AgentSpec) -> None:
        from core.config import FEATURE_FLAGS
        if not FEATURE_FLAGS.get("enable_legacy_agents", False):
            raise RuntimeError("Legacy agents are disabled by Phase 2 architecture rules.")
        self._agents[spec.name.lower()] = spec'''
content = re.sub(r'    def register\(self, spec: AgentSpec\) -> None:.*?self\._agents\[spec\.name\.lower\(\)\] = spec', new_register, content, flags=re.DOTALL)

# Replace dispatch()
new_dispatch = '''    def dispatch(self, user_message: str) -> DispatchResult:
        from core.config import FEATURE_FLAGS
        if not FEATURE_FLAGS.get("enable_legacy_agents", False):
            raise RuntimeError("Legacy agents are disabled by Phase 2 architecture rules.")'''
content = re.sub(r'    def dispatch\(self, user_message: str\) -> DispatchResult:', new_dispatch, content)

with open('core/agents/registry.py', 'w', encoding='utf-8') as f:
    f.write(content)
