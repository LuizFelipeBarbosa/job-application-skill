import { HostedDashboard } from "./hosted-dashboard";
import { requireChatGPTUser } from "./chatgpt-auth";

export default async function Home() {
  await requireChatGPTUser("/");
  return <HostedDashboard />;
}
