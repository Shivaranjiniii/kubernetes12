const { ApolloServer } = require("apollo-server-fastify");
const { ApolloGateway } = require("@apollo/gateway");
const {
  ApolloServerPluginDrainHttpServer,
  ApolloServerPluginLandingPageGraphQLPlayground,
} = require("apollo-server-core");
const fastify = require("fastify");

const serviceList = [
  {
    name: "saleor",
    url: "https://w8-saleor-staging.herokuapp.com/graphql/",
  },
  // {
  //   name: "social-login",
  //   url: `https://w8-saleor-pr-${process.env.PR_NUMBER}.herokuapp.com/plugins/social-login/graphql`,
  // }
];

function fastifyAppClosePlugin(app) {
  return {
    async serverWillStart() {
      return {
        async drainServer() {
          await app.close();
        },
      };
    },
  };
}

(async function () {
  const gateway = new ApolloGateway({ serviceList });
  const app = fastify();
  const server = new ApolloServer({
    gateway,
    plugins: [
      fastifyAppClosePlugin(app),
      ApolloServerPluginLandingPageGraphQLPlayground({
        httpServer: app.server,
      }),
    ],
  });

  server
    .start()
    .then(() => app.register(server.createHandler()))
    .then(() => app.listen(process.env.PORT || 4000))
    .then(() => {
      console.log(`🚀  Gateway is ready at ${server.graphqlPath}`);
    })
    .catch((err) => {
      console.error(err);
    });
})();
