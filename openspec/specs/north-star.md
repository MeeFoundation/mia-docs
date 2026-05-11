# North Star

Where the Mee identity agent project is headed. See our [identity agents](https://idagent.mee.foundation/identity-agents.pdf) paper.

## Vision

We envision a digital world where people are free to live as they wish, free to share whatever they choose with whomever they wish, and empowered with identity agents that work entirely on their behalf. 

### Independence, freedom, autonomy

People have digital identities that are independent of government and big tech. This life-long digital identity is controlled by the individual and is not created by governments or corporations. These identity agents follow a local-first design philosophy that reduces a far as possible, dependence on web services managed by entities other than the individual.

### Control

Control of personal data shifts to the individual. People are empowered with trusted *identity agents* that represent them in the digital world, and work on their behalf. 

### Privacy

People tell their agents what to share with whom (other identity agent users or companies). The information travels over a peer-to-peer communications network.

## Product design philosophy

Meet people where they are and lead them to a better future. 

* For example "where they are" means the agent imports the person's contacts (e.g. from Apple Contacts). "A better future" means now he person has the ability to make selected contacts auto-updating by inviting the other person to use Mee. 

## What's a Mee identity agent? (MIA)

MIA is a software application that runs on your devices, with minimal use of cloud-based servers. It has the following components:

* A UI that allows the user to (i) view, update, organize their personal information held in a local datastore and/or in other PDN nodes, (ii) create *connections* and (iii) manage *integrations*.
* The user's data is stored in a personal datastore within the application. It adheres to the Persona ontology.
* A *connection* is a internet communications channel between nodes on the Personal Data Network (PDN). Each Mia is a PDN node. Service providers can integrate as nodes on the PDN.
* An *integration* is implemented as a connector between the personal datastore and some external OS service or local application.
* A bundled browser extension to implement GPC and MySignals

## Features

## Over time we will add features to the agent. We need to sort them into [roadmap](https://plane.mee.foundation/mee/projects/c7ef98b7-8daf-4db3-9849-cf6a9c8a765d/issues/).

| **Feature** | **Description** |
|---------|-------------|
| Contact sharing | Invite another Mia user to create a bidirectional data sharing connection, sharing contact information (think vcard initially).  |
| Document sharing | Share documents between two Mia users, including the ability to delegate access |
| Global Privacy Control | Send GPC signal to websites you visit |
| Text messaging | Server-less text messaging between two Mia users |
| SEDI wallet | Accepts, holds and presents SEDI (KERI) credentials |
| Groups  | Group chat and shared data/documents. |