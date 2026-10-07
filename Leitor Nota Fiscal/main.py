from config import LOG_DIR
from gui import App, configurar_logging


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    configurar_logging()
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.ao_fechar)
    app.mainloop()


if __name__ == "__main__":
    main()
