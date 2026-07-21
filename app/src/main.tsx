import "@mantine/core/styles.css";
import "./theme/global.css";

import { MantineProvider } from "@mantine/core";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { whubCssVariablesResolver } from "./theme/colors";
import { theme } from "./theme/theme";

createRoot(document.getElementById("root")!).render(
  <MantineProvider
    cssVariablesResolver={whubCssVariablesResolver}
    defaultColorScheme="auto"
    theme={theme}
  >
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </MantineProvider>,
);
