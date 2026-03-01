import { defineRouteMiddleware } from "@astrojs/starlight/route-data";

export const onRequest = defineRouteMiddleware((context) => {
  const { head } = context.locals.starlightRoute;
  const generatorMeta = head.find(
    (entry: any) =>
      entry.tag === "meta" &&
      entry.attrs?.name === "generator" &&
      typeof entry.attrs.content === "string" &&
      entry.attrs.content.startsWith("Starlight v")
  );

  if (generatorMeta && generatorMeta.attrs) {
    generatorMeta.attrs.content = generatorMeta.attrs.content.replace(
      /^Starlight /,
      "Starlight (Ion) "
    );
  }
});
