"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import CandidateList from "@/components/CandidateList";
import CandidateProfile from "@/components/CandidateProfile";
import AdminDashboard from "@/components/AdminDashboard";
import JobsScreen from "@/components/JobsScreen";
import LoginCard from "@/components/LoginCard";
import ResumeInbox from "@/components/ResumeInbox";
import { fetchMe, resetAllAtsData, SessionError, type Me } from "@/lib/api";

type Tab = "dashboard" | "candidates" | "jobs" | "inbox";
const SESSION_TOKEN_KEY = "aksats.session-token";

function getStoredToken() {
  const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
  if (token) return token;

  const legacyToken = window.sessionStorage.getItem(SESSION_TOKEN_KEY);
  if (legacyToken) {
    window.localStorage.setItem(SESSION_TOKEN_KEY, legacyToken);
    window.sessionStorage.removeItem(SESSION_TOKEN_KEY);
  }
  return legacyToken;
}

function storeToken(token: string) {
  window.localStorage.setItem(SESSION_TOKEN_KEY, token);
  window.sessionStorage.removeItem(SESSION_TOKEN_KEY);
}

function clearStoredToken() {
  window.localStorage.removeItem(SESSION_TOKEN_KEY);
  window.sessionStorage.removeItem(SESSION_TOKEN_KEY);
}

export default function AppShell() {
  const [session, setSession] = useState<{ token: string; me: Me } | null>(null);
  const [restoringSession, setRestoringSession] = useState(true);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("candidates");
  const [openId, setOpenId] = useState<number | null>(null);
  const [startEditingProfile, setStartEditingProfile] = useState(false);
  const [resetting, setResetting] = useState(false);
  const restoreSession = useCallback(async () => {
    setRestoringSession(true);
    setRestoreError(null);
    let token: string | null;
    try {
      token = getStoredToken();
    } catch {
      setRestoreError("This browser could not access saved session data. Enable site storage and retry.");
      setRestoringSession(false);
      return;
    }

    if (!token) {
      setSession(null);
      setRestoringSession(false);
      return;
    }

    try {
      const me = await fetchMe(token);
      setSession({ token, me });
    } catch (error) {
      if (error instanceof SessionError) {
        try {
          clearStoredToken();
        } catch {
          setRestoreError("Your session expired, and this browser could not clear it. Enable site storage and retry.");
        }
        setSession(null);
      } else {
        setRestoreError(error instanceof Error ? error.message : "Could not restore your session");
      }
    } finally {
      setRestoringSession(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const restoreInitialSession = async () => {
      try {
        const token = getStoredToken();
        if (!token) {
          if (!cancelled) setRestoringSession(false);
          return;
        }
        const me = await fetchMe(token);
        if (!cancelled) setSession({ token, me });
      } catch (error) {
        if (cancelled) return;
        if (error instanceof SessionError) {
          try {
            clearStoredToken();
            setRestoringSession(false);
          } catch {
            setRestoreError("Your session expired, and this browser could not clear it. Enable site storage and retry.");
            setRestoringSession(false);
          }
          return;
        }
        setRestoreError(error instanceof Error ? error.message : "Could not restore your session");
      } finally {
        if (!cancelled) setRestoringSession(false);
      }
    };
    void restoreInitialSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const endSession = useCallback(() => {
    try {
      clearStoredToken();
    } catch {
      setRestoreError("Could not clear the saved session. Clear this site's browser data before sharing this device.");
    }
    setOpenId(null);
    setSession(null);
  }, []);
  const handleSignedIn = useCallback((token: string, me: Me) => {
    try {
      storeToken(token);
      setRestoreError(null);
    } catch {
      setRestoreError("Signed in, but this browser cannot preserve your session. Enable site storage.");
    }
    setTab("candidates");
    setOpenId(null);
    setSession({ token, me });
  }, []);
  const closeProfile = useCallback(() => {
    setOpenId(null);
    setStartEditingProfile(false);
  }, []);

  const openCandidate = useCallback((id: number, edit = false) => {
    setOpenId(id);
    setStartEditingProfile(edit);
  }, []);

  const handleReset = useCallback(async () => {
    if (!session) return;
    const confirmed = window.confirm("This will delete all jobs, candidates, resume records, and uploaded files. Continue?");
    if (!confirmed) return;

    setResetting(true);
    try {
      const result = await resetAllAtsData(session.token);
      window.alert(result.message || "ATS data reset complete.");
      setOpenId(null);
      setTab("candidates");
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Reset failed");
    } finally {
      setResetting(false);
    }
  }, [session]);

  if (restoringSession) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <div className="glass p-10 text-center" role="status">Restoring your session...</div>
      </main>
    );
  }

  if (!session && restoreError) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <section className="glass w-full max-w-md p-8 text-center">
          <p className="form-error" role="alert">{restoreError}</p>
          <div className="mt-4 flex justify-center gap-3">
            <button className="btn-dark" onClick={() => void restoreSession()}>Retry</button>
            <button className="btn-ghost" onClick={endSession}>Sign in again</button>
          </div>
        </section>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <LoginCard onSignedIn={handleSignedIn} />
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
          <Image
            className="company-logo-header"
            src="/company-logo.png"
            alt="All Known Services"
            width={512}
            height={127}
            priority
          />
          <nav className="tabs" aria-label="Main">
            {session.me.permissions.includes("user.manage") && (
              <button className={"tab" + (tab === "dashboard" ? " on" : "")} onClick={() => go("dashboard")}>Dashboard</button>
            )}
            <button className={"tab" + (tab === "candidates" ? " on" : "")} onClick={() => go("candidates")}>Candidates</button>
            <button className={"tab" + (tab === "jobs" ? " on" : "")} onClick={() => go("jobs")}>Jobs</button>
            <button className={"tab" + (tab === "inbox" ? " on" : "")} onClick={() => go("inbox")}>Resume Inbox</button>
          </nav>
          <div className="who">
            <div className="who-text">
              <span className="who-name">{session.me.full_name}</span>
              <span className="who-mail">{session.me.email}</span>
            </div>
            <span className="chip">{session.me.designation ?? session.me.roles.join(", ")}</span>

            {session.me.permissions.includes("ats.reset") &&
              session.me.email.toLowerCase() === "vamshi@allknownservices.com" && (
              <button className="btn-ghost" onClick={handleReset} disabled={resetting}>
                {resetting ? "Resetting..." : "Reset ATS"}
              </button>
            )}
            <button className="btn-ghost" onClick={endSession}>Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl p-4 sm:p-6">
        {tab === "dashboard" && session.me.permissions.includes("user.manage") ? (
          <AdminDashboard key="dashboard" token={session.token} onSessionEnd={endSession} />
        ) : tab === "inbox" ? (
          <ResumeInbox key="i" token={session.token} onSessionEnd={endSession} />
        ) : tab === "jobs" ? (
          <JobsScreen key="j" token={session.token} onSessionEnd={endSession}
            canManageJobs={session.me.permissions.includes("job.manage")}
            canDeleteJobs={session.me.permissions.includes("job.delete")}
            onOpenCandidate={(id) => { setTab("candidates"); openCandidate(id); }} />
        ) : openId !== null ? (
          <CandidateProfile key={`p${openId}`} token={session.token} id={openId}
            canEdit={session.me.permissions.includes("candidate.edit")}
            canUploadDocuments={session.me.permissions.includes("document.upload")}
            startEditing={startEditingProfile} onBack={closeProfile} onSessionEnd={endSession} />
        ) : (
          <CandidateList key="c" token={session.token} onSessionEnd={endSession}
            canEdit={session.me.permissions.includes("candidate.edit")}
            canArchive={session.me.permissions.includes("candidate.archive")}
            canDelete={session.me.permissions.includes("candidate.delete")} onOpen={openCandidate} />
        )}
      </main>
    </div>
  );
}