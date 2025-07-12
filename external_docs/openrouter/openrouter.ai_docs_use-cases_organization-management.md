---
url: "https://openrouter.ai/docs/use-cases/organization-management"
title: "OpenRouter Organization Management | Developer Documentation | OpenRouter | Documentation"
---

OpenRouter organizations enable teams and companies to collaborate effectively by sharing credits, managing API keys centrally, and tracking usage across all team members. Organizations are ideal for companies that want to pool resources, manage inference costs centrally, and maintain oversight of AI usage across their team.

## Getting Started with Organizations

### Creating an Organization

To create an organization:

1. Navigate to [Settings > Preferences](https://openrouter.ai/settings/preferences)
2. In the Organization section, click **Create Organization**
3. Follow the setup process to configure your organization details
4. Invite team members to join your organization

You must have a verified email address to create an organization.

### Switching Between Personal and Organization Accounts

Once you’re part of an organization, you can easily switch between your personal account and organization context:

- Use the **organization switcher** at the top of the web application
- When in organization mode, all actions (API usage, credit purchases, key management) are performed on behalf of the organization
- When in personal mode, you’re working with your individual account resources

## Credit Management

### Shared Credit Pool

Organizations maintain a shared credit pool that offers several advantages:

- **Centralized Billing**: All credits purchased in the organization account can be used by any organization member
- **Simplified Accounting**: Track all AI inference costs in one place
- **Budget Control**: Administrators can manage spending and monitor usage across the entire team

### Admin-Only Credit Management

Only organization administrators can:

- Purchase credits for the organization
- View detailed billing information
- Manage payment methods and invoicing settings

Regular organization members cannot purchase credits or access billing information. Contact your organization administrator for credit-related requests.

### Transferring Credits from Personal to Organization

If you need to transfer credits from your personal account to your organization account:

1. Email [support@openrouter.ai](mailto:support@openrouter.ai) with your request
2. Include your organization details and the amount you wish to transfer
3. Our support team will process the transfer manually

Credit transfers from personal to organization accounts require manual processing by our support team and cannot be done automatically through the interface.

## API Key Management

Organizations provide flexible API key management with role-based permissions:

### Member Permissions

- **Create API Keys**: All organization members can create API keys
- **View Own Keys**: Members can only view and manage API keys they created
- **Use Organization Keys**: Keys created by any organization member can be used by all members
- **Shared Usage**: API usage from any organization key is billed to the organization’s credit pool

### Administrator Permissions

- **View All Keys**: Administrators can view all API keys created within the organization
- **Manage All Keys**: Full access to edit, disable, or delete any organization API key
- **Monitor Usage**: Access to detailed usage analytics for all organization keys

When creating API keys within an organization, consider using descriptive names that indicate the key’s purpose or the team member responsible for it.

## Activity and Usage Tracking

### Organization-Wide Activity Feed

When viewing your activity feed while in organization context, you’ll see:

- **All Member Activity**: Usage data from all organization members appears in the activity feed
- **Metadata Only**: Activity shows model usage, costs, and request metadata
- **Key Filtering**: Activity can be filtered by a specific API key to view usage for that key only

**Known Limitation**: The activity feed currently shows all organization member activity when in organization context, not just your individual activity. Usage metadata (model used, cost, timing) is visible to all organization members.

### Usage Analytics

Organizations benefit from comprehensive usage analytics:

- Track spending across all team members
- Monitor model usage patterns
- Identify cost optimization opportunities
- Generate reports for budget planning

## Administrative Controls

### Admin-Only Settings

Organization administrators have exclusive access to:

- **Provider Settings**: Configure preferred model providers and routing preferences
- **Privacy Settings**: Manage data retention and privacy policies for the organization
- **Member Management**: Add, remove, and manage member roles
- **Billing Configuration**: Set up invoicing, payment methods, and billing contacts

### Member Role Management

Organizations support role-based access control:

- **Admin**: Full access to all organization features and settings
- **Member**: Access to create keys, use organization resources, and view own activity

## Use Cases and Benefits

### For Development Teams

- **Shared Resources**: Pool credits across multiple developers and projects
- **Centralized Management**: Manage all API keys and usage from a single dashboard
- **Cost Tracking**: Monitor spending per project or team member
- **Simplified Onboarding**: New team members can immediately access organization resources

### For Companies

- **Budget Control**: Administrators control spending and resource allocation
- **Compliance**: Centralized logging and usage tracking for audit purposes
- **Scalability**: Easy to add new team members and projects
- **Cost Optimization**: Identify usage patterns and optimize model selection

### For Research Organizations

- **Resource Sharing**: Share expensive model access across research teams
- **Usage Monitoring**: Track research spending and resource utilization
- **Collaboration**: Enable seamless collaboration on AI projects
- **Reporting**: Generate usage reports for grant applications and budget planning

## Frequently Asked Questions

###### Can I convert my personal account to an organization?

No, organizations are separate entities. You’ll need to create a new organization and transfer resources as needed. Contact [support@openrouter.ai](mailto:support@openrouter.ai) for assistance with credit transfers.

###### How many members can an organization have?

An organization can only have 10 members. Contact support if you need more.

###### Can organization members see each other's usage data?

Organization members can see usage metadata (model used, cost, timing) for all organization activity in the activity feed. OpenRouter does not store prompts or responses.

###### What happens if I leave an organization?

When you leave an organization, you lose access to organization resources, credits, and API keys. Your personal account remains unaffected.

###### Can I be a member of multiple organizations?

Yes, you can be a member of multiple organizations and switch between them using the organization switcher.

## Getting Help

If you need assistance with organization management:

- **General Questions**: Check our [FAQ](https://openrouter.ai/docs/faq) for common questions
- **Technical Support**: Email [support@openrouter.ai](mailto:support@openrouter.ai)
- **Credit Transfers**: Email [support@openrouter.ai](mailto:support@openrouter.ai) with transfer requests
- **Enterprise Sales**: Contact our sales team for large organization needs

Organizations make it easy to collaborate on AI projects while maintaining control over costs and resources. Get started by creating your organization today!