import { ChatWindow } from "@/components/chat-window";

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden p-4 md:p-10">
      <div className="pointer-events-none absolute -left-28 top-8 h-64 w-64 rounded-full bg-[#a8e2ff]/50 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-10 h-72 w-72 rounded-full bg-[#c8eeff]/45 blur-3xl" />
      <div className="relative">
        <ChatWindow />
      </div>
    </main>
  );
}
