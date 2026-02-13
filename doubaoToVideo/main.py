from dify_plugin import Plugin
from dify_plugin.config.config import DifyPluginEnv

plugin = Plugin(DifyPluginEnv())

if __name__ == "__main__":
    plugin.run()
