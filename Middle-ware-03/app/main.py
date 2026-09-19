from app.tracing.provider import configure_tracing


configure_tracing()


def main():
    print("Clinical Middleware started")


if __name__ == "__main__":
    main()