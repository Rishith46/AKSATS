"use client";

import { useCallback, useState } from "react";
import CandidateList from "@/components/CandidateList";
import CandidateProfile from "@/components/CandidateProfile";
import JobsScreen from "@/components/JobsScreen";
import LoginCard from "@/components/LoginCard";
import ResumeInbox from "@/components/ResumeInbox";
import type { Me } from "@/lib/api";

type Tab = "candidates" | "jobs" | "inbox";

export default function AppShell() {
  const [session, setSession] = useState<{ token: string; me: Me } | null>(null);
  const [tab, setTab] = useState<Tab>("candidates");
  const [openId, setOpenId] = useState<number | null>(null);
  const endSession = useCallback(() => { setOpenId(null); setSession(null); }, []);
  const closeProfile = useCallback(() => setOpenId(null), []);

  if (!session) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <LoginCard onSignedIn={(token, me) => { setTab("candidates"); setOpenId(null); setSession({ token, me }); }} />
      </main>
    );
  }

  function go(t: Tab) {
    setOpenId(null);
    setTab(t);
  }

  return (
    <div className="min-h-screen">
      <header className="topbar">
        <div className="topbar-inner">
          <span className="brand">All Known Services</span>
          <nav className="tabs" aria-label="Main">
            <button className={"tab" + (tab === "candidates" ? " on" : "")} onClick={() => go("candidates")}>Candidates</button>
            <button className={"tab" + (tab === "jobs" ? " on" : "")} onClick={() => go("jobs")}>Jobs</button>
            <button className={"tab" + (tab === "inbox" ? " on" : "")} onClick={() => go("inbox")}>Resume Inbox</button>
          </nav>
          <div className="who">
            <div className="who-text">
              <span className="who-name">{session.me.full_name}</span>
              <span className="who-mail">{session.me.email}</span>
            </div>
            {session.me.roles.map((r) => (
              <span key={r} className="chip">{r}</span>
            ))}
            <button className="btn-ghost" onClick={endSession}>Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl p-4 sm:p-6">
        {tab === "inbox" ? (
          <ResumeInbox key="i" token={session.token} onSessionEnd={endSession} />
        ) : tab === "jobs" ? (
          <JobsScreen key="j" token={session.token} onSessionEnd={endSession} onOpenCandidate={(id) => { setTab("candidates"); setOpenId(id); }} />
        ) : openId !== null ? (
          <CandidateProfile key={`p${openId}`} token={session.token} id={openId} onBack={closeProfile} onSessionEnd={endSession} />
        ) : (
          <CandidateList key="c" token={session.token} onSessionEnd={endSession} onOpen={setOpenId} />
        )}
      </main>
    </div>
  );
}