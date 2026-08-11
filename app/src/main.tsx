import "@mantine/core/styles.css";
import "@mantine/code-highlight/styles.css";
import "./theme/global.css";

import {
  CodeHighlightAdapterProvider,
  createHighlightJsAdapter,
} from "@mantine/code-highlight";
import { MantineProvider } from "@mantine/core";
import hljs from "highlight.js/lib/common";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { whubCssVariablesResolver } from "./theme/colors";
import { theme } from "./theme/theme";

createRoot(document.getElementById("root")!).render(
  <CodeHighlightAdapterProvider adapter={createHighlightJsAdapter(hljs)}>
    <MantineProvider
      cssVariablesResolver={whubCssVariablesResolver}
      defaultColorScheme="auto"
      theme={theme}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MantineProvider>
  </CodeHighlightAdapterProvider>,
);
