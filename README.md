[![Version](https://img.shields.io/github/v/release/etalab-ia/OpenGateLLM?color=blue&label=version)](https://github.com/etalab-ia/OpenGateLLM/releases)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/OpenGateLLM/refs/heads/main/.github/badges/coverage.json)](https://github.com/etalab-ia/OpenGateLLM)
[![License](https://img.shields.io/github/license/etalab-ia/OpenGateLLM?color=green&label=license)](https://github.com/etalab-ia/OpenGateLLM/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/etalab-ia/OpenGateLLM?color=yellow&label=stars)](https://github.com/etalab-ia/OpenGateLLM/stargazers)

<img src="./docs/static/img/logo.svg" alt="Logo" width="128" height="128">

# OpenGateLLM
### **[Documentation](https://docs.opengatellm.org) | [API Reference](https://albert.api.etalab.gouv.fr/reference)**

> [!WARNING]
> **The API is still under beta version, major breaking changes may occur.**


OpenGateLLM is an open-source, production-ready API gateway, optimized for self-hosted models. It's designed to centralize, secure, and manage Generative AI access in a sovereign and cost-effective way.

OpenGateLLM addresses three critical challenges for organizations:
1. **Cost control** - Reduce expenses of commercial APIs and GPU infrastructure by using self-hosted models and build a mutualized infrastructure with your peers.
2. **Data sovereignty** - Keep sensitive data under your control
3. **Privacy & security** - No chat history storage, robust access control

**Core principles**

- Open source and free forever - All features available without commercial licensing
- High code quality - Built with maintainability and reliability in mind
- Lightweight architecture - Focused feature set for optimal performance
- High compatibility - Seamlessly integrates with GenAI ecosystem frameworks by OpenAI-compatible API
- Production-ready - Engineered to handle high loads with advanced QoS features

![OpenGateLLM architecture](docs/static/img/ogl_architecture.png)

**OpenGateLLM is an alternative to...**

<table>
    <thead>
        <tr>
            <th style={{width: '58%', textAlign: 'center', fontWeight: 'bold'}}>Key features</th>
            <th style={{width: '14%', textAlign: 'center', fontWeight: 'bold'}}>OpenGateLLM</th>
            <th style={{width: '14%', textAlign: 'center', fontWeight: 'bold'}}>LiteLLM</th>
            <th style={{width: '14%', textAlign: 'center', fontWeight: 'bold'}}>TensorZero</th>
        </tr>
    </thead>
    <tbody>
        <tr><td>:electric_plug: OpenAI Compatibility</td><td>✅</td><td>✅</td><td>✅</td></tr>
        <tr><td>:open_book: [Open-source](https://github.com/etalab-ia/OpenGateLLM)</td><td>✅</td><td>✅</td><td>✅</td></tr>
        <tr><td>:computer: [Self-hostable](./getting-started/quickstart.md)</td><td>✅</td><td>✅</td><td>✅</td></tr>
        <tr><td>:money_with_wings: <b>Free (all features)</b></td><td>✅</td><td>❌</td><td>✅</td></tr>
        <tr><td>:factory: Support commercial and self-hosted models</td><td>✅</td><td>✅</td><td>✅</td></tr>
        <!-- User management -->
        <tr><td colSpan={4} style={{textAlign: 'center'}}><b>Account management</b></td></tr>
        <tr><td>:game_die: Playground UI</td><td>✅</td><td>✅</td><td>✅</td></tr>
        <tr><td>:bust_in_silhouette: User management (API keys, budget...)</td><td>✅</td><td>✅</td><td>✅</td></tr>
        <tr><td>:office: Organization management</td><td>🚧</td><td>✅</td><td>❌</td></tr>
        <tr><td>:pencil2: Project management</td><td>🔜</td><td>✅</td><td>❌</td></tr>
        <tr><td>:key: SSO support</td><td>🚧</td><td>✅</td><td>❌</td></tr>
        <!-- High load optimization -->
        <tr><td colSpan={4} style={{textAlign: 'center'}}><b>High load features</b></td></tr>
        <tr><td>:hourglass: Rate limiting</td><td>✅</td><td>❌</td><td>❌</td></tr>
        <tr><td>:zap: Requests prioritization</td><td>✅</td><td>✅</td><td>❌</td></tr>
        <tr><td>:chart_with_upwards_trend: Quality of service thresholds</td><td>✅</td><td>✅</td><td>❌</td></tr>
        <tr><td>:twisted_rightwards_arrows: Model load balancing</td><td>✅</td><td>✅</td><td>❌</td></tr>
        <tr><td>:arrows_counterclockwise: Model fallback</td><td>🔜</td><td>✅</td><td>❌</td></tr>
        <!-- Monitoring & analytics -->
        <tr><td colSpan={4} style={{textAlign: 'center'}}><b>Monitoring & analytics</b></td></tr>
        <tr><td>:bar_chart: Usage tracking</td><td>✅</td><td>❌</td><td>❌</td></tr>
        <tr><td>:chart_with_upwards_trend: Carbon footprint</td><td>✅</td><td>❌</td><td>❌</td></tr>
        <tr><td>:link: Prometheus integration</td><td>✅</td><td>❌</td><td>❌</td></tr>
        <!-- Privacy & security -->
        <tr><td colSpan={4} style={{textAlign: 'center'}}><b>Privacy & security</b></td></tr>
        <tr><td>:no_entry_sign: No chat history storage</td><td>✅</td><td>❌</td><td>❌</td></tr>
        <tr><td>:lock: Role-based access control</td><td>✅</td><td>❌</td><td>❌</td></tr>
    </tbody>
</table>

Legend: *✅ supported* — *❌ not supported* — *🚧 work in progress* — *🔜 in roadmap*

### 🚀 Quickstart
***
Deploy and start using OpenGateLLM in minutes with our quickstart guide [here](https://docs.opengatellm.org/docs/getting-started/quickstart).

### 🤝 Contribute
***

This project exists thanks to all the people who contribute. OpenGateLLM thrives on open-source contributions. Join our community! 

Check out our [Contribution Guide](https://docs.opengatellm.org/docs/contributing) to get started.

### 🗺️ Roadmap
***

OpenGateLLM is still under *beta version*, major breaking changes may occur. Check our current roadmap [here](https://github.com/etalab-ia/OpenGateLLM/discussions/425) to see what we are working on.


### 🎖️ Sponsors
***

<div id="toc">
  <ul align="center" style="list-style: none">
<a href="https://www.numerique.gouv.fr/numerique-etat/dinum/" ><img src="./docs/static/img/dinum_logo.png" alt="DINUM logo" width="300" style="margin-right: 40px"></a>
<a href="https://www.centralesupelec.fr"><img src="./docs/static/img/centralsupelec_logo.png" alt="CentraleSupélec logo" width="200" style="margin-right: 40px"></a>
  </ul>
</div>
