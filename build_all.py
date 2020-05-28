# Run the client and addon build scripts.
import build_client
import build_addon


def build():
    client_path = build_client.build()
    addon_path = build_addon.build()


if __name__ == "__main__":
    build()
