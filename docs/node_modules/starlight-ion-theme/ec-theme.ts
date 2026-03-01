import githubDark from "@shikijs/themes/github-dark";
import githubLight from "@shikijs/themes/github-light";
import type { ThemeRegistration } from "shiki";

const ionDark: ThemeRegistration = {
  ...githubDark,
  name: "Ion Dark",
  colors: {
    ...githubDark.colors,
    "activityBar.background": "#121212",
    "editor.background": "#121212",
    "statusBar.background": "#121212",
    "statusBarItem.remoteBackground": "#121212",
    "tab.activeBackground": "#121212",
    "titleBar.activeBackground": "#121212",
    "editorGroupHeader.tabsBackground": "#262626",
    "panel.background": "#121212",
  },
};

const ionLight: ThemeRegistration = {
  ...githubLight,
  name: "Ion Light",
  colors: {
    ...githubLight.colors,
    "activityBar.background": "#ffffff",
    "editor.background": "#ffffff",
    "statusBar.background": "#ffffff",
    "statusBarItem.remoteBackground": "#ffffff",
    "tab.activeBackground": "#ffffff",
    "titleBar.activeBackground": "#ffffff",
    "editorGroupHeader.tabsBackground": "#e0e0e0",
    "panel.background": "#ffffff",
  },
};

export { ionDark, ionLight };
