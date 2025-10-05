--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (63f4182)
-- Dumped by pg_dump version 16.9

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: cleanup_expired_saves(); Type: FUNCTION; Schema: public; Owner: neondb_owner
--

CREATE FUNCTION public.cleanup_expired_saves() RETURNS void
    LANGUAGE plpgsql
    AS $$
                BEGIN
                    DELETE FROM miniapp_saves WHERE expires_at <= NOW();
                END;
                $$;


ALTER FUNCTION public.cleanup_expired_saves() OWNER TO neondb_owner;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ad_messages; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.ad_messages (
    id bigint NOT NULL,
    session_id bigint,
    user_id bigint,
    anon_name text,
    msg_type text NOT NULL,
    content text,
    meta jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.ad_messages OWNER TO neondb_owner;

--
-- Name: ad_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.ad_messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ad_messages_id_seq OWNER TO neondb_owner;

--
-- Name: ad_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.ad_messages_id_seq OWNED BY public.ad_messages.id;


--
-- Name: ad_participants; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.ad_participants (
    id bigint NOT NULL,
    session_id bigint,
    user_id bigint NOT NULL,
    anon_name text NOT NULL,
    joined_at timestamp with time zone DEFAULT now(),
    left_at timestamp with time zone
);


ALTER TABLE public.ad_participants OWNER TO neondb_owner;

--
-- Name: ad_participants_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.ad_participants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ad_participants_id_seq OWNER TO neondb_owner;

--
-- Name: ad_participants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.ad_participants_id_seq OWNED BY public.ad_participants.id;


--
-- Name: ad_prompts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.ad_prompts (
    id bigint NOT NULL,
    session_id bigint,
    kind text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.ad_prompts OWNER TO neondb_owner;

--
-- Name: ad_prompts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.ad_prompts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ad_prompts_id_seq OWNER TO neondb_owner;

--
-- Name: ad_prompts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.ad_prompts_id_seq OWNED BY public.ad_prompts.id;


--
-- Name: ad_sessions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.ad_sessions (
    id bigint NOT NULL,
    started_at timestamp with time zone DEFAULT now(),
    ends_at timestamp with time zone NOT NULL,
    vibe text,
    status text DEFAULT 'live'::text
);


ALTER TABLE public.ad_sessions OWNER TO neondb_owner;

--
-- Name: ad_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.ad_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ad_sessions_id_seq OWNER TO neondb_owner;

--
-- Name: ad_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.ad_sessions_id_seq OWNED BY public.ad_sessions.id;


--
-- Name: blocked_users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.blocked_users (
    user_id bigint NOT NULL,
    blocked_uid bigint NOT NULL,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.blocked_users OWNER TO neondb_owner;

--
-- Name: chat_extensions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.chat_extensions (
    id integer NOT NULL,
    match_id bigint NOT NULL,
    extended_by bigint NOT NULL,
    stars_paid integer DEFAULT 50,
    minutes_added integer DEFAULT 30,
    extended_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.chat_extensions OWNER TO neondb_owner;

--
-- Name: chat_extensions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.chat_extensions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_extensions_id_seq OWNER TO neondb_owner;

--
-- Name: chat_extensions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.chat_extensions_id_seq OWNED BY public.chat_extensions.id;


--
-- Name: chat_ratings; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.chat_ratings (
    id integer NOT NULL,
    rater_id bigint NOT NULL,
    ratee_id bigint NOT NULL,
    value smallint NOT NULL,
    reason text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.chat_ratings OWNER TO neondb_owner;

--
-- Name: chat_ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.chat_ratings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_ratings_id_seq OWNER TO neondb_owner;

--
-- Name: chat_ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.chat_ratings_id_seq OWNED BY public.chat_ratings.id;


--
-- Name: chat_reports; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.chat_reports (
    id bigint NOT NULL,
    reporter_tg_id bigint NOT NULL,
    reported_tg_id bigint NOT NULL,
    in_secret boolean DEFAULT false NOT NULL,
    text text,
    media_file_id text,
    media_type text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.chat_reports OWNER TO neondb_owner;

--
-- Name: chat_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.chat_reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_reports_id_seq OWNER TO neondb_owner;

--
-- Name: chat_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.chat_reports_id_seq OWNED BY public.chat_reports.id;


--
-- Name: comment_likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.comment_likes (
    comment_id bigint NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.comment_likes OWNER TO neondb_owner;

--
-- Name: comments; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.comments (
    id integer NOT NULL,
    post_id integer,
    user_id bigint,
    text text,
    created_at timestamp without time zone,
    pinned boolean DEFAULT false NOT NULL,
    pinned_at timestamp with time zone,
    pinned_by_user_id integer,
    profile_id bigint
);


ALTER TABLE public.comments OWNER TO neondb_owner;

--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.comments_id_seq OWNER TO neondb_owner;

--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: confession_deliveries; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confession_deliveries (
    id bigint NOT NULL,
    confession_id bigint NOT NULL,
    user_id bigint NOT NULL,
    delivered_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.confession_deliveries OWNER TO neondb_owner;

--
-- Name: confession_deliveries_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.confession_deliveries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.confession_deliveries_id_seq OWNER TO neondb_owner;

--
-- Name: confession_deliveries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.confession_deliveries_id_seq OWNED BY public.confession_deliveries.id;


--
-- Name: confession_leaderboard; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confession_leaderboard (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    period character varying(20) NOT NULL,
    confession_count integer DEFAULT 0,
    total_reactions_received integer DEFAULT 0,
    replies_received integer DEFAULT 0,
    rank_type character varying(30) NOT NULL,
    rank_position integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.confession_leaderboard OWNER TO neondb_owner;

--
-- Name: confession_leaderboard_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.confession_leaderboard_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.confession_leaderboard_id_seq OWNER TO neondb_owner;

--
-- Name: confession_leaderboard_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.confession_leaderboard_id_seq OWNED BY public.confession_leaderboard.id;


--
-- Name: confession_mutes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confession_mutes (
    user_id bigint NOT NULL,
    confession_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.confession_mutes OWNER TO neondb_owner;

--
-- Name: confession_reactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confession_reactions (
    id bigint NOT NULL,
    confession_id bigint NOT NULL,
    user_id bigint NOT NULL,
    reaction_type character varying(10) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    approved boolean DEFAULT false,
    approved_at timestamp with time zone
);


ALTER TABLE public.confession_reactions OWNER TO neondb_owner;

--
-- Name: confession_reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.confession_reactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.confession_reactions_id_seq OWNER TO neondb_owner;

--
-- Name: confession_reactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.confession_reactions_id_seq OWNED BY public.confession_reactions.id;


--
-- Name: confession_replies; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confession_replies (
    id bigint NOT NULL,
    original_confession_id bigint NOT NULL,
    replier_user_id bigint NOT NULL,
    reply_text text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    reply_reactions integer DEFAULT 0,
    is_anonymous boolean DEFAULT true,
    approved boolean DEFAULT false,
    approved_at timestamp with time zone
);


ALTER TABLE public.confession_replies OWNER TO neondb_owner;

--
-- Name: confession_replies_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.confession_replies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.confession_replies_id_seq OWNER TO neondb_owner;

--
-- Name: confession_replies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.confession_replies_id_seq OWNED BY public.confession_replies.id;


--
-- Name: confession_stats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confession_stats (
    user_id bigint NOT NULL,
    total_confessions integer DEFAULT 0,
    weekly_confessions integer DEFAULT 0,
    current_streak integer DEFAULT 0,
    longest_streak integer DEFAULT 0,
    total_reactions_received integer DEFAULT 0,
    total_replies_received integer DEFAULT 0,
    best_confessor_score integer DEFAULT 0,
    last_confession_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.confession_stats OWNER TO neondb_owner;

--
-- Name: confessions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.confessions (
    id integer NOT NULL,
    author_id bigint NOT NULL,
    text text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    delivered boolean DEFAULT false,
    delivered_at timestamp with time zone,
    delivered_to bigint,
    system_seed boolean DEFAULT false,
    deleted_at timestamp with time zone
);


ALTER TABLE public.confessions OWNER TO neondb_owner;

--
-- Name: confessions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.confessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.confessions_id_seq OWNER TO neondb_owner;

--
-- Name: confessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.confessions_id_seq OWNED BY public.confessions.id;


--
-- Name: crush_leaderboard; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.crush_leaderboard (
    user_id bigint NOT NULL,
    crush_count integer DEFAULT 0,
    week_start date DEFAULT CURRENT_DATE,
    last_updated timestamp with time zone DEFAULT now()
);


ALTER TABLE public.crush_leaderboard OWNER TO neondb_owner;

--
-- Name: daily_dare_selection; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.daily_dare_selection (
    dare_date date NOT NULL,
    dare_text text NOT NULL,
    dare_source character varying(20) DEFAULT 'community'::character varying,
    source_id integer,
    created_at timestamp with time zone DEFAULT now(),
    submitter_id bigint,
    category character varying(20) DEFAULT 'general'::character varying,
    difficulty character varying(10) DEFAULT 'medium'::character varying,
    creator_notified boolean DEFAULT false
);


ALTER TABLE public.daily_dare_selection OWNER TO neondb_owner;

--
-- Name: dare_feedback; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.dare_feedback (
    id integer NOT NULL,
    submission_id integer,
    event_type character varying(20),
    user_id bigint,
    dare_date date,
    notified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT dare_feedback_event_type_check CHECK (((event_type)::text = ANY ((ARRAY['selected'::character varying, 'accepted'::character varying, 'completed'::character varying])::text[])))
);


ALTER TABLE public.dare_feedback OWNER TO neondb_owner;

--
-- Name: dare_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.dare_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dare_feedback_id_seq OWNER TO neondb_owner;

--
-- Name: dare_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.dare_feedback_id_seq OWNED BY public.dare_feedback.id;


--
-- Name: dare_responses; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.dare_responses (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    dare_date date NOT NULL,
    response character varying(10),
    response_time timestamp with time zone DEFAULT now(),
    completion_claimed boolean DEFAULT false,
    difficulty_selected character varying(10) DEFAULT 'medium'::character varying,
    dare_text text,
    CONSTRAINT dare_responses_response_check CHECK (((response)::text = ANY ((ARRAY['accepted'::character varying, 'declined'::character varying, 'expired'::character varying])::text[])))
);


ALTER TABLE public.dare_responses OWNER TO neondb_owner;

--
-- Name: dare_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.dare_responses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dare_responses_id_seq OWNER TO neondb_owner;

--
-- Name: dare_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.dare_responses_id_seq OWNED BY public.dare_responses.id;


--
-- Name: dare_stats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.dare_stats (
    user_id bigint NOT NULL,
    current_streak integer DEFAULT 0,
    longest_streak integer DEFAULT 0,
    total_accepted integer DEFAULT 0,
    total_declined integer DEFAULT 0,
    total_expired integer DEFAULT 0,
    last_dare_date date,
    badges text[] DEFAULT '{}'::text[],
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.dare_stats OWNER TO neondb_owner;

--
-- Name: dare_submissions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.dare_submissions (
    id integer NOT NULL,
    submitter_id bigint NOT NULL,
    dare_text text NOT NULL,
    category character varying(20) DEFAULT 'general'::character varying,
    difficulty character varying(10) DEFAULT 'medium'::character varying,
    approved boolean DEFAULT false,
    admin_approved_by bigint,
    submission_date date DEFAULT CURRENT_DATE,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.dare_submissions OWNER TO neondb_owner;

--
-- Name: dare_submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.dare_submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dare_submissions_id_seq OWNER TO neondb_owner;

--
-- Name: dare_submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.dare_submissions_id_seq OWNED BY public.dare_submissions.id;


--
-- Name: fantasy_board_reactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_board_reactions (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    fantasy_id bigint NOT NULL,
    reaction_type text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.fantasy_board_reactions OWNER TO neondb_owner;

--
-- Name: fantasy_board_reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_board_reactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_board_reactions_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_board_reactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_board_reactions_id_seq OWNED BY public.fantasy_board_reactions.id;


--
-- Name: fantasy_chat_sessions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_chat_sessions (
    id bigint NOT NULL,
    a_id bigint NOT NULL,
    b_id bigint NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    status text DEFAULT 'active'::text NOT NULL
);


ALTER TABLE public.fantasy_chat_sessions OWNER TO neondb_owner;

--
-- Name: fantasy_chat_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_chat_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_chat_sessions_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_chat_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_chat_sessions_id_seq OWNED BY public.fantasy_chat_sessions.id;


--
-- Name: fantasy_chats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_chats (
    id integer NOT NULL,
    match_id integer,
    chat_room_id text NOT NULL,
    started_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone DEFAULT (now() + '00:15:00'::interval),
    boy_joined boolean DEFAULT false,
    girl_joined boolean DEFAULT false,
    message_count integer DEFAULT 0
);


ALTER TABLE public.fantasy_chats OWNER TO neondb_owner;

--
-- Name: fantasy_chats_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_chats_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_chats_id_seq OWNED BY public.fantasy_chats.id;


--
-- Name: fantasy_match_notifs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_match_notifs (
    id integer NOT NULL,
    match_id integer,
    user_id bigint NOT NULL,
    sent_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.fantasy_match_notifs OWNER TO neondb_owner;

--
-- Name: fantasy_match_notifs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_match_notifs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_match_notifs_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_match_notifs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_match_notifs_id_seq OWNED BY public.fantasy_match_notifs.id;


--
-- Name: fantasy_match_requests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_match_requests (
    id integer NOT NULL,
    requester_id bigint NOT NULL,
    fantasy_id bigint NOT NULL,
    fantasy_owner_id bigint NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    responded_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    cancelled_by_user_id bigint,
    cancelled_at timestamp with time zone,
    cancel_reason text,
    version integer DEFAULT 1
);


ALTER TABLE public.fantasy_match_requests OWNER TO neondb_owner;

--
-- Name: fantasy_match_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_match_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_match_requests_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_match_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_match_requests_id_seq OWNED BY public.fantasy_match_requests.id;


--
-- Name: fantasy_matches; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_matches (
    id integer NOT NULL,
    boy_id bigint NOT NULL,
    girl_id bigint NOT NULL,
    fantasy_key text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone DEFAULT (now() + '24:00:00'::interval),
    boy_ready boolean DEFAULT false,
    girl_ready boolean DEFAULT false,
    boy_is_premium boolean DEFAULT false,
    connected_at timestamp without time zone,
    status character varying(20) DEFAULT 'pending'::character varying,
    chat_id text,
    vibe text,
    shared_keywords text[]
);


ALTER TABLE public.fantasy_matches OWNER TO neondb_owner;

--
-- Name: fantasy_matches_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_matches_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_matches_id_seq OWNED BY public.fantasy_matches.id;


--
-- Name: fantasy_stats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_stats (
    fantasy_id bigint NOT NULL,
    views_count integer DEFAULT 0,
    reactions_count integer DEFAULT 0,
    matches_count integer DEFAULT 0,
    success_rate numeric(5,2) DEFAULT 0.0,
    last_updated timestamp with time zone DEFAULT now()
);


ALTER TABLE public.fantasy_stats OWNER TO neondb_owner;

--
-- Name: fantasy_submissions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.fantasy_submissions (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    gender text NOT NULL,
    fantasy_text text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    is_active boolean DEFAULT true,
    fantasy_key text,
    submitted_count integer DEFAULT 1,
    vibe text,
    keywords text[],
    active boolean DEFAULT true
);


ALTER TABLE public.fantasy_submissions OWNER TO neondb_owner;

--
-- Name: fantasy_submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.fantasy_submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fantasy_submissions_id_seq OWNER TO neondb_owner;

--
-- Name: fantasy_submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.fantasy_submissions_id_seq OWNED BY public.fantasy_submissions.id;


--
-- Name: feed_comments; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.feed_comments (
    id bigint NOT NULL,
    post_id bigint,
    author_id bigint NOT NULL,
    author_name text NOT NULL,
    text text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.feed_comments OWNER TO neondb_owner;

--
-- Name: feed_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.feed_comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feed_comments_id_seq OWNER TO neondb_owner;

--
-- Name: feed_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.feed_comments_id_seq OWNED BY public.feed_comments.id;


--
-- Name: feed_likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.feed_likes (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.feed_likes OWNER TO neondb_owner;

--
-- Name: feed_posts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.feed_posts (
    id bigint NOT NULL,
    author_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    content_type text,
    file_id text,
    text text,
    reaction_count integer DEFAULT 0,
    comment_count integer DEFAULT 0,
    profile_id bigint
);


ALTER TABLE public.feed_posts OWNER TO neondb_owner;

--
-- Name: feed_posts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.feed_posts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feed_posts_id_seq OWNER TO neondb_owner;

--
-- Name: feed_posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.feed_posts_id_seq OWNED BY public.feed_posts.id;


--
-- Name: feed_profiles; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.feed_profiles (
    uid bigint NOT NULL,
    username text,
    bio text,
    is_public boolean DEFAULT true,
    photo text
);


ALTER TABLE public.feed_profiles OWNER TO neondb_owner;

--
-- Name: feed_reactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.feed_reactions (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    emoji text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.feed_reactions OWNER TO neondb_owner;

--
-- Name: feed_views; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.feed_views (
    post_id bigint NOT NULL,
    viewer_id bigint NOT NULL,
    viewed_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.feed_views OWNER TO neondb_owner;

--
-- Name: friend_chats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.friend_chats (
    id bigint NOT NULL,
    a bigint,
    b bigint,
    opened_at timestamp with time zone DEFAULT now(),
    closed_at timestamp with time zone
);


ALTER TABLE public.friend_chats OWNER TO neondb_owner;

--
-- Name: friend_chats_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.friend_chats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.friend_chats_id_seq OWNER TO neondb_owner;

--
-- Name: friend_chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.friend_chats_id_seq OWNED BY public.friend_chats.id;


--
-- Name: friend_msg_requests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.friend_msg_requests (
    id bigint NOT NULL,
    sender bigint,
    receiver bigint,
    text text,
    created_at timestamp with time zone DEFAULT now(),
    status text DEFAULT 'pending'::text
);


ALTER TABLE public.friend_msg_requests OWNER TO neondb_owner;

--
-- Name: friend_msg_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.friend_msg_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.friend_msg_requests_id_seq OWNER TO neondb_owner;

--
-- Name: friend_msg_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.friend_msg_requests_id_seq OWNED BY public.friend_msg_requests.id;


--
-- Name: friend_requests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.friend_requests (
    requester_id bigint NOT NULL,
    target_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.friend_requests OWNER TO neondb_owner;

--
-- Name: friends; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.friends (
    user_id bigint NOT NULL,
    friend_id bigint NOT NULL,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.friends OWNER TO neondb_owner;

--
-- Name: friendship_levels; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.friendship_levels (
    user1_id bigint NOT NULL,
    user2_id bigint NOT NULL,
    interaction_count integer DEFAULT 0,
    level integer DEFAULT 1,
    last_interaction timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.friendship_levels OWNER TO neondb_owner;

--
-- Name: game_questions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.game_questions (
    game text,
    question text,
    added_by bigint,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.game_questions OWNER TO neondb_owner;

--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.idempotency_keys (
    key text NOT NULL,
    operation text NOT NULL,
    result jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.idempotency_keys OWNER TO neondb_owner;

--
-- Name: likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.likes (
    id integer NOT NULL,
    post_id integer,
    user_id bigint,
    created_at timestamp without time zone
);


ALTER TABLE public.likes OWNER TO neondb_owner;

--
-- Name: likes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.likes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.likes_id_seq OWNER TO neondb_owner;

--
-- Name: likes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.likes_id_seq OWNED BY public.likes.id;


--
-- Name: maintenance_log; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.maintenance_log (
    id bigint NOT NULL,
    operation text NOT NULL,
    status text NOT NULL,
    details jsonb,
    duration_seconds real,
    executed_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.maintenance_log OWNER TO neondb_owner;

--
-- Name: maintenance_log_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.maintenance_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.maintenance_log_id_seq OWNER TO neondb_owner;

--
-- Name: maintenance_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.maintenance_log_id_seq OWNED BY public.maintenance_log.id;


--
-- Name: miniapp_comments; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_comments (
    id bigint NOT NULL,
    post_id bigint NOT NULL,
    author_id bigint NOT NULL,
    text text NOT NULL,
    parent_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT miniapp_comments_text_check CHECK (((length(text) >= 1) AND (length(text) <= 500)))
);


ALTER TABLE public.miniapp_comments OWNER TO neondb_owner;

--
-- Name: miniapp_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.miniapp_comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.miniapp_comments_id_seq OWNER TO neondb_owner;

--
-- Name: miniapp_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.miniapp_comments_id_seq OWNED BY public.miniapp_comments.id;


--
-- Name: miniapp_follows; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_follows (
    follower_id bigint NOT NULL,
    followee_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'approved'::text NOT NULL,
    CONSTRAINT miniapp_follows_check CHECK ((follower_id <> followee_id)),
    CONSTRAINT miniapp_follows_status_check CHECK ((status = ANY (ARRAY['approved'::text, 'pending'::text])))
);


ALTER TABLE public.miniapp_follows OWNER TO neondb_owner;

--
-- Name: miniapp_likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_likes (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.miniapp_likes OWNER TO neondb_owner;

--
-- Name: miniapp_post_views; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_post_views (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    viewed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.miniapp_post_views OWNER TO neondb_owner;

--
-- Name: miniapp_posts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_posts (
    id bigint NOT NULL,
    author_id bigint NOT NULL,
    type text DEFAULT 'text'::text NOT NULL,
    caption text,
    media_url text,
    media_type text,
    visibility text DEFAULT 'public'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT miniapp_posts_caption_check CHECK ((length(caption) <= 2000)),
    CONSTRAINT miniapp_posts_type_check CHECK ((type = ANY (ARRAY['text'::text, 'photo'::text, 'video'::text]))),
    CONSTRAINT miniapp_posts_visibility_check CHECK ((visibility = ANY (ARRAY['public'::text, 'followers'::text, 'private'::text]))),
    CONSTRAINT valid_media CHECK ((((type = 'text'::text) AND (media_url IS NULL)) OR ((type = ANY (ARRAY['photo'::text, 'video'::text])) AND (media_url IS NOT NULL))))
);


ALTER TABLE public.miniapp_posts OWNER TO neondb_owner;

--
-- Name: miniapp_posts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.miniapp_posts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.miniapp_posts_id_seq OWNER TO neondb_owner;

--
-- Name: miniapp_posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.miniapp_posts_id_seq OWNED BY public.miniapp_posts.id;


--
-- Name: miniapp_profiles; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_profiles (
    user_id bigint NOT NULL,
    username text,
    display_name text,
    bio text,
    avatar_url text,
    is_private boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT miniapp_profiles_bio_check CHECK (((bio IS NULL) OR (length(bio) <= 500))),
    CONSTRAINT miniapp_profiles_display_name_check CHECK (((display_name IS NULL) OR (length(display_name) <= 100))),
    CONSTRAINT miniapp_profiles_username_check CHECK (((username IS NULL) OR ((length(username) >= 3) AND (length(username) <= 30))))
);


ALTER TABLE public.miniapp_profiles OWNER TO neondb_owner;

--
-- Name: miniapp_saves; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.miniapp_saves (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '72:00:00'::interval) NOT NULL,
    CONSTRAINT miniapp_saves_check CHECK ((expires_at > created_at))
);


ALTER TABLE public.miniapp_saves OWNER TO neondb_owner;

--
-- Name: moderation_events; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.moderation_events (
    id bigint NOT NULL,
    tg_user_id bigint,
    kind text NOT NULL,
    token text NOT NULL,
    sample text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.moderation_events OWNER TO neondb_owner;

--
-- Name: moderation_events_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.moderation_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.moderation_events_id_seq OWNER TO neondb_owner;

--
-- Name: moderation_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.moderation_events_id_seq OWNED BY public.moderation_events.id;


--
-- Name: muc_char_options; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_char_options (
    id integer NOT NULL,
    question_id integer NOT NULL,
    opt_key text NOT NULL,
    text text NOT NULL
);


ALTER TABLE public.muc_char_options OWNER TO neondb_owner;

--
-- Name: muc_char_options_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_char_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_char_options_id_seq OWNER TO neondb_owner;

--
-- Name: muc_char_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_char_options_id_seq OWNED BY public.muc_char_options.id;


--
-- Name: muc_char_questions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_char_questions (
    id integer NOT NULL,
    series_id integer NOT NULL,
    prompt text NOT NULL,
    question_key text NOT NULL,
    active_from_episode_id integer
);


ALTER TABLE public.muc_char_questions OWNER TO neondb_owner;

--
-- Name: muc_char_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_char_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_char_questions_id_seq OWNER TO neondb_owner;

--
-- Name: muc_char_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_char_questions_id_seq OWNED BY public.muc_char_questions.id;


--
-- Name: muc_char_votes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_char_votes (
    id integer NOT NULL,
    question_id integer NOT NULL,
    option_id integer NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.muc_char_votes OWNER TO neondb_owner;

--
-- Name: muc_char_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_char_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_char_votes_id_seq OWNER TO neondb_owner;

--
-- Name: muc_char_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_char_votes_id_seq OWNED BY public.muc_char_votes.id;


--
-- Name: muc_characters; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_characters (
    id integer NOT NULL,
    series_id integer NOT NULL,
    name text NOT NULL,
    role text NOT NULL,
    bio_md text,
    attributes jsonb DEFAULT '{}'::jsonb,
    secrets jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.muc_characters OWNER TO neondb_owner;

--
-- Name: muc_characters_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_characters_id_seq OWNER TO neondb_owner;

--
-- Name: muc_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_characters_id_seq OWNED BY public.muc_characters.id;


--
-- Name: muc_episodes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_episodes (
    id integer NOT NULL,
    series_id integer NOT NULL,
    idx integer NOT NULL,
    title text NOT NULL,
    teaser_md text,
    body_md text,
    cliff_md text,
    publish_at timestamp with time zone,
    close_at timestamp with time zone,
    status text DEFAULT 'draft'::text NOT NULL,
    CONSTRAINT muc_episodes_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'published'::text, 'voting'::text, 'closed'::text])))
);


ALTER TABLE public.muc_episodes OWNER TO neondb_owner;

--
-- Name: muc_episodes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_episodes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_episodes_id_seq OWNER TO neondb_owner;

--
-- Name: muc_episodes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_episodes_id_seq OWNED BY public.muc_episodes.id;


--
-- Name: muc_poll_options; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_poll_options (
    id integer NOT NULL,
    poll_id integer NOT NULL,
    opt_key text,
    text text NOT NULL,
    next_hint text,
    idx integer DEFAULT 0
);


ALTER TABLE public.muc_poll_options OWNER TO neondb_owner;

--
-- Name: muc_poll_options_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_poll_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_poll_options_id_seq OWNER TO neondb_owner;

--
-- Name: muc_poll_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_poll_options_id_seq OWNED BY public.muc_poll_options.id;


--
-- Name: muc_polls; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_polls (
    id integer NOT NULL,
    episode_id integer NOT NULL,
    prompt text NOT NULL,
    layer text DEFAULT 'surface'::text NOT NULL,
    allow_multi boolean DEFAULT false,
    CONSTRAINT muc_polls_layer_check CHECK ((layer = ANY (ARRAY['surface'::text, 'deeper'::text, 'deepest'::text])))
);


ALTER TABLE public.muc_polls OWNER TO neondb_owner;

--
-- Name: muc_polls_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_polls_id_seq OWNER TO neondb_owner;

--
-- Name: muc_polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_polls_id_seq OWNED BY public.muc_polls.id;


--
-- Name: muc_series; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_series (
    id integer NOT NULL,
    slug text NOT NULL,
    title text NOT NULL,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.muc_series OWNER TO neondb_owner;

--
-- Name: muc_series_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_series_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_series_id_seq OWNER TO neondb_owner;

--
-- Name: muc_series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_series_id_seq OWNED BY public.muc_series.id;


--
-- Name: muc_theories; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_theories (
    id integer NOT NULL,
    episode_id integer NOT NULL,
    user_id bigint NOT NULL,
    text text NOT NULL,
    likes integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.muc_theories OWNER TO neondb_owner;

--
-- Name: muc_theories_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_theories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_theories_id_seq OWNER TO neondb_owner;

--
-- Name: muc_theories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_theories_id_seq OWNED BY public.muc_theories.id;


--
-- Name: muc_theory_likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_theory_likes (
    id integer NOT NULL,
    theory_id integer NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.muc_theory_likes OWNER TO neondb_owner;

--
-- Name: muc_theory_likes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_theory_likes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_theory_likes_id_seq OWNER TO neondb_owner;

--
-- Name: muc_theory_likes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_theory_likes_id_seq OWNED BY public.muc_theory_likes.id;


--
-- Name: muc_user_engagement; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_user_engagement (
    user_id bigint NOT NULL,
    streak_days integer DEFAULT 0,
    detective_score integer DEFAULT 0,
    last_seen_episode_id integer
);


ALTER TABLE public.muc_user_engagement OWNER TO neondb_owner;

--
-- Name: muc_votes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.muc_votes (
    id integer NOT NULL,
    poll_id integer NOT NULL,
    option_id integer NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.muc_votes OWNER TO neondb_owner;

--
-- Name: muc_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.muc_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.muc_votes_id_seq OWNER TO neondb_owner;

--
-- Name: muc_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.muc_votes_id_seq OWNED BY public.muc_votes.id;


--
-- Name: naughty_wyr_deliveries; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.naughty_wyr_deliveries (
    question_id bigint NOT NULL,
    user_id bigint NOT NULL,
    delivered_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.naughty_wyr_deliveries OWNER TO neondb_owner;

--
-- Name: naughty_wyr_questions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.naughty_wyr_questions (
    id bigint NOT NULL,
    question text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    system_seed boolean DEFAULT true
);


ALTER TABLE public.naughty_wyr_questions OWNER TO neondb_owner;

--
-- Name: naughty_wyr_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.naughty_wyr_questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.naughty_wyr_questions_id_seq OWNER TO neondb_owner;

--
-- Name: naughty_wyr_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.naughty_wyr_questions_id_seq OWNED BY public.naughty_wyr_questions.id;


--
-- Name: naughty_wyr_votes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.naughty_wyr_votes (
    question_id bigint NOT NULL,
    user_id bigint NOT NULL,
    choice text NOT NULL,
    voted_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.naughty_wyr_votes OWNER TO neondb_owner;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id bigint,
    ntype character varying(24),
    actor bigint,
    post_id integer,
    created_at timestamp without time zone,
    read boolean,
    comment_id bigint
);


ALTER TABLE public.notifications OWNER TO neondb_owner;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO neondb_owner;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: pending_confession_replies; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.pending_confession_replies (
    id integer NOT NULL,
    original_confession_id bigint NOT NULL,
    replier_user_id bigint NOT NULL,
    reply_text text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    admin_notified boolean DEFAULT false,
    is_voice boolean DEFAULT false,
    voice_file_id text,
    voice_duration integer
);


ALTER TABLE public.pending_confession_replies OWNER TO neondb_owner;

--
-- Name: pending_confession_replies_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.pending_confession_replies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pending_confession_replies_id_seq OWNER TO neondb_owner;

--
-- Name: pending_confession_replies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.pending_confession_replies_id_seq OWNED BY public.pending_confession_replies.id;


--
-- Name: pending_confessions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.pending_confessions (
    id bigint NOT NULL,
    author_id bigint NOT NULL,
    text text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    admin_notified boolean DEFAULT false,
    is_voice boolean DEFAULT false,
    voice_file_id text,
    voice_duration integer
);


ALTER TABLE public.pending_confessions OWNER TO neondb_owner;

--
-- Name: pending_confessions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.pending_confessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pending_confessions_id_seq OWNER TO neondb_owner;

--
-- Name: pending_confessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.pending_confessions_id_seq OWNED BY public.pending_confessions.id;


--
-- Name: poll_options; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.poll_options (
    id bigint NOT NULL,
    poll_id bigint NOT NULL,
    text text NOT NULL
);


ALTER TABLE public.poll_options OWNER TO neondb_owner;

--
-- Name: poll_options_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.poll_options_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_options_id_seq OWNER TO neondb_owner;

--
-- Name: poll_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.poll_options_id_seq OWNED BY public.poll_options.id;


--
-- Name: poll_votes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.poll_votes (
    poll_id bigint NOT NULL,
    voter_id bigint NOT NULL,
    option_idx integer NOT NULL,
    voted_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.poll_votes OWNER TO neondb_owner;

--
-- Name: polls; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.polls (
    id bigint NOT NULL,
    author_id bigint NOT NULL,
    question text NOT NULL,
    options text[] NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.polls OWNER TO neondb_owner;

--
-- Name: polls_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.polls_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.polls_id_seq OWNER TO neondb_owner;

--
-- Name: polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.polls_id_seq OWNED BY public.polls.id;


--
-- Name: post_likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.post_likes (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.post_likes OWNER TO neondb_owner;

--
-- Name: post_reports; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.post_reports (
    id bigint NOT NULL,
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    reason text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.post_reports OWNER TO neondb_owner;

--
-- Name: post_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.post_reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.post_reports_id_seq OWNER TO neondb_owner;

--
-- Name: post_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.post_reports_id_seq OWNED BY public.post_reports.id;


--
-- Name: posts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.posts (
    id integer NOT NULL,
    author bigint,
    text text,
    media_url text,
    is_public boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.posts OWNER TO neondb_owner;

--
-- Name: posts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.posts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.posts_id_seq OWNER TO neondb_owner;

--
-- Name: posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.posts_id_seq OWNED BY public.posts.id;


--
-- Name: profiles; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.profiles (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    profile_name text NOT NULL,
    username text NOT NULL,
    bio text,
    avatar_url text,
    is_active boolean DEFAULT false
);


ALTER TABLE public.profiles OWNER TO neondb_owner;

--
-- Name: profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.profiles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.profiles_id_seq OWNER TO neondb_owner;

--
-- Name: profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.profiles_id_seq OWNED BY public.profiles.id;


--
-- Name: qa_answers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.qa_answers (
    id bigint NOT NULL,
    question_id bigint NOT NULL,
    author_id bigint NOT NULL,
    text text NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.qa_answers OWNER TO neondb_owner;

--
-- Name: qa_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.qa_answers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.qa_answers_id_seq OWNER TO neondb_owner;

--
-- Name: qa_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.qa_answers_id_seq OWNED BY public.qa_answers.id;


--
-- Name: qa_questions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.qa_questions (
    id bigint NOT NULL,
    author_id bigint,
    text text NOT NULL,
    scope text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.qa_questions OWNER TO neondb_owner;

--
-- Name: qa_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.qa_questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.qa_questions_id_seq OWNER TO neondb_owner;

--
-- Name: qa_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.qa_questions_id_seq OWNED BY public.qa_questions.id;


--
-- Name: referrals; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.referrals (
    inviter_id bigint NOT NULL,
    invitee_id bigint NOT NULL,
    rewarded boolean DEFAULT false,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.referrals OWNER TO neondb_owner;

--
-- Name: reports; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.reports (
    id bigint NOT NULL,
    reporter bigint NOT NULL,
    target bigint NOT NULL,
    reason text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.reports OWNER TO neondb_owner;

--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reports_id_seq OWNER TO neondb_owner;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.reports_id_seq OWNED BY public.reports.id;


--
-- Name: secret_chats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.secret_chats (
    id bigint NOT NULL,
    a bigint NOT NULL,
    b bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone NOT NULL,
    closed_at timestamp with time zone
);


ALTER TABLE public.secret_chats OWNER TO neondb_owner;

--
-- Name: secret_chats_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.secret_chats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.secret_chats_id_seq OWNER TO neondb_owner;

--
-- Name: secret_chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.secret_chats_id_seq OWNED BY public.secret_chats.id;


--
-- Name: secret_crush; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.secret_crush (
    user_id bigint NOT NULL,
    target_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.secret_crush OWNER TO neondb_owner;

--
-- Name: sensual_reactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.sensual_reactions (
    id bigint NOT NULL,
    story_id bigint,
    user_id bigint NOT NULL,
    reaction text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.sensual_reactions OWNER TO neondb_owner;

--
-- Name: sensual_reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.sensual_reactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sensual_reactions_id_seq OWNER TO neondb_owner;

--
-- Name: sensual_reactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.sensual_reactions_id_seq OWNED BY public.sensual_reactions.id;


--
-- Name: sensual_stories; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.sensual_stories (
    id bigint NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    category text DEFAULT 'general'::text,
    created_at timestamp with time zone DEFAULT now(),
    is_featured boolean DEFAULT false
);


ALTER TABLE public.sensual_stories OWNER TO neondb_owner;

--
-- Name: sensual_stories_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.sensual_stories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sensual_stories_id_seq OWNER TO neondb_owner;

--
-- Name: sensual_stories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.sensual_stories_id_seq OWNED BY public.sensual_stories.id;


--
-- Name: social_comments; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.social_comments (
    id integer NOT NULL,
    post_id integer,
    user_tg_id bigint NOT NULL,
    text text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.social_comments OWNER TO neondb_owner;

--
-- Name: social_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.social_comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.social_comments_id_seq OWNER TO neondb_owner;

--
-- Name: social_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.social_comments_id_seq OWNED BY public.social_comments.id;


--
-- Name: social_friend_requests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.social_friend_requests (
    id integer NOT NULL,
    requester_tg_id bigint NOT NULL,
    target_tg_id bigint NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.social_friend_requests OWNER TO neondb_owner;

--
-- Name: social_friend_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.social_friend_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.social_friend_requests_id_seq OWNER TO neondb_owner;

--
-- Name: social_friend_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.social_friend_requests_id_seq OWNED BY public.social_friend_requests.id;


--
-- Name: social_friends; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.social_friends (
    id integer NOT NULL,
    user_tg_id bigint NOT NULL,
    friend_tg_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.social_friends OWNER TO neondb_owner;

--
-- Name: social_friends_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.social_friends_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.social_friends_id_seq OWNER TO neondb_owner;

--
-- Name: social_friends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.social_friends_id_seq OWNED BY public.social_friends.id;


--
-- Name: social_likes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.social_likes (
    id integer NOT NULL,
    post_id integer,
    user_tg_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.social_likes OWNER TO neondb_owner;

--
-- Name: social_likes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.social_likes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.social_likes_id_seq OWNER TO neondb_owner;

--
-- Name: social_likes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.social_likes_id_seq OWNED BY public.social_likes.id;


--
-- Name: social_posts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.social_posts (
    id integer NOT NULL,
    author_tg_id bigint NOT NULL,
    text text DEFAULT ''::text,
    media character varying(255),
    is_public boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.social_posts OWNER TO neondb_owner;

--
-- Name: social_posts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.social_posts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.social_posts_id_seq OWNER TO neondb_owner;

--
-- Name: social_posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.social_posts_id_seq OWNED BY public.social_posts.id;


--
-- Name: social_profiles; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.social_profiles (
    id integer NOT NULL,
    tg_user_id bigint NOT NULL,
    username character varying(50),
    bio text DEFAULT ''::text,
    photo character varying(255),
    privacy character varying(20) DEFAULT 'public'::character varying,
    show_fields text DEFAULT 'username,bio,photo'::text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.social_profiles OWNER TO neondb_owner;

--
-- Name: social_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.social_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.social_profiles_id_seq OWNER TO neondb_owner;

--
-- Name: social_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.social_profiles_id_seq OWNED BY public.social_profiles.id;


--
-- Name: stories; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.stories (
    id bigint NOT NULL,
    author_id bigint NOT NULL,
    kind text NOT NULL,
    text text,
    media_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.stories OWNER TO neondb_owner;

--
-- Name: stories_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.stories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stories_id_seq OWNER TO neondb_owner;

--
-- Name: stories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.stories_id_seq OWNED BY public.stories.id;


--
-- Name: story_segments; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.story_segments (
    id integer NOT NULL,
    story_id bigint NOT NULL,
    segment_type text NOT NULL,
    content_type text NOT NULL,
    file_id text,
    text text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    user_id bigint,
    profile_id bigint
);


ALTER TABLE public.story_segments OWNER TO neondb_owner;

--
-- Name: story_segments_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.story_segments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.story_segments_id_seq OWNER TO neondb_owner;

--
-- Name: story_segments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.story_segments_id_seq OWNED BY public.story_segments.id;


--
-- Name: story_views; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.story_views (
    id bigint NOT NULL,
    story_id bigint NOT NULL,
    user_id bigint NOT NULL,
    viewed_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.story_views OWNER TO neondb_owner;

--
-- Name: story_views_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.story_views_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.story_views_id_seq OWNER TO neondb_owner;

--
-- Name: story_views_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.story_views_id_seq OWNED BY public.story_views.id;


--
-- Name: user_badges; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_badges (
    user_id bigint NOT NULL,
    badge_id text NOT NULL,
    earned_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_badges OWNER TO neondb_owner;

--
-- Name: user_blocks; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_blocks (
    blocker_id bigint NOT NULL,
    blocked_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_blocks OWNER TO neondb_owner;

--
-- Name: user_follows; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_follows (
    follower_id bigint NOT NULL,
    followee_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_follows OWNER TO neondb_owner;

--
-- Name: user_interests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_interests (
    user_id integer,
    interest_key text NOT NULL
);


ALTER TABLE public.user_interests OWNER TO neondb_owner;

--
-- Name: user_mutes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_mutes (
    muter_id bigint NOT NULL,
    muted_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_mutes OWNER TO neondb_owner;

--
-- Name: users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.users (
    id integer NOT NULL,
    tg_user_id bigint NOT NULL,
    gender text,
    age integer,
    country text,
    city text,
    is_premium boolean DEFAULT false,
    search_pref text DEFAULT 'any'::text,
    created_at timestamp without time zone DEFAULT now(),
    last_dialog_date date,
    dialogs_total integer DEFAULT 0,
    dialogs_today integer DEFAULT 0,
    messages_sent integer DEFAULT 0,
    messages_recv integer DEFAULT 0,
    rating_up integer DEFAULT 0,
    rating_down integer DEFAULT 0,
    report_count integer DEFAULT 0,
    is_verified boolean DEFAULT false,
    verify_status text DEFAULT 'none'::text,
    verify_method text,
    verify_audio_file text,
    verify_photo_file text,
    verify_phrase text,
    verify_at timestamp without time zone,
    verify_src_chat bigint,
    verify_src_msg bigint,
    premium_until timestamp without time zone,
    language text,
    last_gender_change_at timestamp with time zone,
    last_age_change_at timestamp with time zone,
    banned_until timestamp with time zone,
    banned_reason text,
    banned_by bigint,
    match_verified_only boolean DEFAULT false,
    incognito boolean DEFAULT false,
    coins integer DEFAULT 0,
    last_daily timestamp with time zone,
    strikes integer DEFAULT 0,
    last_strike timestamp with time zone,
    spin_last timestamp with time zone,
    spins integer DEFAULT 0,
    games_played integer DEFAULT 0,
    bio text,
    photo_file_id text,
    feed_username text,
    feed_is_public boolean DEFAULT true,
    feed_photo text,
    feed_notify boolean DEFAULT true,
    date_of_birth date,
    shadow_banned boolean DEFAULT false,
    shadow_banned_at timestamp with time zone,
    min_age_pref integer DEFAULT 18,
    max_age_pref integer DEFAULT 99,
    allow_forward boolean DEFAULT false,
    last_seen timestamp with time zone,
    wyr_streak integer DEFAULT 0,
    wyr_last_voted date,
    dare_streak integer DEFAULT 0,
    dare_last_date date,
    vault_tokens integer DEFAULT 10,
    vault_tokens_last_reset date DEFAULT CURRENT_DATE,
    vault_storage_used bigint DEFAULT 0,
    vault_coins integer DEFAULT 0,
    display_name text,
    username text,
    avatar_url text,
    is_onboarded boolean DEFAULT false NOT NULL,
    tg_id bigint,
    active_profile_id bigint,
    CONSTRAINT chk_users_age_range CHECK (((age IS NULL) OR ((age >= 13) AND (age <= 120))))
);


ALTER TABLE public.users OWNER TO neondb_owner;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO neondb_owner;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: vault_categories; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.vault_categories (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    emoji text DEFAULT '📝'::text,
    blur_intensity integer DEFAULT 70,
    premium_only boolean DEFAULT true,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.vault_categories OWNER TO neondb_owner;

--
-- Name: vault_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.vault_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vault_categories_id_seq OWNER TO neondb_owner;

--
-- Name: vault_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.vault_categories_id_seq OWNED BY public.vault_categories.id;


--
-- Name: vault_content; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.vault_content (
    id bigint NOT NULL,
    submitter_id bigint NOT NULL,
    category_id integer,
    content_text text,
    blurred_text text,
    blur_level integer DEFAULT 70,
    reveal_cost integer DEFAULT 2,
    status text DEFAULT 'pending'::text,
    approval_status text DEFAULT 'pending'::text,
    approved_by bigint,
    approved_at timestamp with time zone,
    view_count integer DEFAULT 0,
    reveal_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    media_type text DEFAULT 'text'::text,
    file_url text,
    thumbnail_url text,
    blurred_thumbnail_url text,
    file_id text,
    CONSTRAINT chk_approval_status CHECK ((approval_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text]))),
    CONSTRAINT chk_media_type CHECK ((media_type = ANY (ARRAY['text'::text, 'image'::text, 'video'::text]))),
    CONSTRAINT chk_vault_status CHECK ((status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'archived'::text])))
);


ALTER TABLE public.vault_content OWNER TO neondb_owner;

--
-- Name: vault_content_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.vault_content_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vault_content_id_seq OWNER TO neondb_owner;

--
-- Name: vault_content_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.vault_content_id_seq OWNED BY public.vault_content.id;


--
-- Name: vault_daily_category_views; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.vault_daily_category_views (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    category_id integer,
    views_today integer DEFAULT 0,
    view_date date DEFAULT CURRENT_DATE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.vault_daily_category_views OWNER TO neondb_owner;

--
-- Name: vault_daily_category_views_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.vault_daily_category_views_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vault_daily_category_views_id_seq OWNER TO neondb_owner;

--
-- Name: vault_daily_category_views_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.vault_daily_category_views_id_seq OWNED BY public.vault_daily_category_views.id;


--
-- Name: vault_daily_limits; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.vault_daily_limits (
    user_id bigint NOT NULL,
    reveals_used integer DEFAULT 0,
    media_reveals_used integer DEFAULT 0,
    limit_date date DEFAULT CURRENT_DATE,
    premium_status boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.vault_daily_limits OWNER TO neondb_owner;

--
-- Name: vault_interactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.vault_interactions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    content_id bigint,
    action text NOT NULL,
    tokens_spent integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chk_vault_action CHECK ((action = ANY (ARRAY['viewed'::text, 'revealed'::text, 'liked'::text, 'reported'::text])))
);


ALTER TABLE public.vault_interactions OWNER TO neondb_owner;

--
-- Name: vault_interactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.vault_interactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vault_interactions_id_seq OWNER TO neondb_owner;

--
-- Name: vault_interactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.vault_interactions_id_seq OWNED BY public.vault_interactions.id;


--
-- Name: vault_user_states; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.vault_user_states (
    user_id bigint NOT NULL,
    category_id integer,
    state text NOT NULL,
    data text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.vault_user_states OWNER TO neondb_owner;

--
-- Name: wyr_anonymous_users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_anonymous_users (
    id bigint NOT NULL,
    vote_date date NOT NULL,
    tg_user_id bigint NOT NULL,
    anonymous_name text NOT NULL,
    assigned_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.wyr_anonymous_users OWNER TO neondb_owner;

--
-- Name: wyr_anonymous_users_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wyr_anonymous_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wyr_anonymous_users_id_seq OWNER TO neondb_owner;

--
-- Name: wyr_anonymous_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wyr_anonymous_users_id_seq OWNED BY public.wyr_anonymous_users.id;


--
-- Name: wyr_group_chats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_group_chats (
    vote_date date NOT NULL,
    total_voters integer DEFAULT 0,
    total_messages integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone DEFAULT (now() + '1 day'::interval)
);


ALTER TABLE public.wyr_group_chats OWNER TO neondb_owner;

--
-- Name: wyr_group_messages; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_group_messages (
    id bigint NOT NULL,
    vote_date date NOT NULL,
    anonymous_user_id bigint,
    message_type text DEFAULT 'comment'::text,
    content text NOT NULL,
    reply_to_message_id bigint,
    created_at timestamp with time zone DEFAULT now(),
    is_deleted boolean DEFAULT false,
    deleted_by_admin bigint,
    deleted_at timestamp with time zone,
    CONSTRAINT wyr_group_messages_message_type_check CHECK ((message_type = ANY (ARRAY['comment'::text, 'reaction'::text, 'reply'::text])))
);


ALTER TABLE public.wyr_group_messages OWNER TO neondb_owner;

--
-- Name: wyr_group_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wyr_group_messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wyr_group_messages_id_seq OWNER TO neondb_owner;

--
-- Name: wyr_group_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wyr_group_messages_id_seq OWNED BY public.wyr_group_messages.id;


--
-- Name: wyr_message_reactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_message_reactions (
    id bigint NOT NULL,
    message_id bigint,
    tg_user_id bigint NOT NULL,
    reaction_type text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT wyr_message_reactions_reaction_type_check CHECK ((reaction_type = ANY (ARRAY['like'::text, 'heart'::text, 'laugh'::text])))
);


ALTER TABLE public.wyr_message_reactions OWNER TO neondb_owner;

--
-- Name: wyr_message_reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wyr_message_reactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wyr_message_reactions_id_seq OWNER TO neondb_owner;

--
-- Name: wyr_message_reactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wyr_message_reactions_id_seq OWNED BY public.wyr_message_reactions.id;


--
-- Name: wyr_permanent_users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_permanent_users (
    tg_user_id bigint NOT NULL,
    permanent_username text NOT NULL,
    assigned_at timestamp with time zone DEFAULT now(),
    total_comments integer DEFAULT 0,
    total_likes integer DEFAULT 0,
    weekly_comments integer DEFAULT 0,
    weekly_likes integer DEFAULT 0,
    last_reset timestamp with time zone DEFAULT now()
);


ALTER TABLE public.wyr_permanent_users OWNER TO neondb_owner;

--
-- Name: wyr_question_of_day; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_question_of_day (
    vote_date date NOT NULL,
    a_text text NOT NULL,
    b_text text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.wyr_question_of_day OWNER TO neondb_owner;

--
-- Name: wyr_votes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wyr_votes (
    tg_user_id bigint NOT NULL,
    vote_date date NOT NULL,
    side character(1) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT wyr_votes_side_check CHECK ((side = ANY (ARRAY['A'::bpchar, 'B'::bpchar])))
);


ALTER TABLE public.wyr_votes OWNER TO neondb_owner;

--
-- Name: ad_messages id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_messages ALTER COLUMN id SET DEFAULT nextval('public.ad_messages_id_seq'::regclass);


--
-- Name: ad_participants id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_participants ALTER COLUMN id SET DEFAULT nextval('public.ad_participants_id_seq'::regclass);


--
-- Name: ad_prompts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_prompts ALTER COLUMN id SET DEFAULT nextval('public.ad_prompts_id_seq'::regclass);


--
-- Name: ad_sessions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_sessions ALTER COLUMN id SET DEFAULT nextval('public.ad_sessions_id_seq'::regclass);


--
-- Name: chat_extensions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chat_extensions ALTER COLUMN id SET DEFAULT nextval('public.chat_extensions_id_seq'::regclass);


--
-- Name: chat_ratings id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chat_ratings ALTER COLUMN id SET DEFAULT nextval('public.chat_ratings_id_seq'::regclass);


--
-- Name: chat_reports id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chat_reports ALTER COLUMN id SET DEFAULT nextval('public.chat_reports_id_seq'::regclass);


--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: confession_deliveries id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_deliveries ALTER COLUMN id SET DEFAULT nextval('public.confession_deliveries_id_seq'::regclass);


--
-- Name: confession_leaderboard id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_leaderboard ALTER COLUMN id SET DEFAULT nextval('public.confession_leaderboard_id_seq'::regclass);


--
-- Name: confession_reactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_reactions ALTER COLUMN id SET DEFAULT nextval('public.confession_reactions_id_seq'::regclass);


--
-- Name: confession_replies id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_replies ALTER COLUMN id SET DEFAULT nextval('public.confession_replies_id_seq'::regclass);


--
-- Name: confessions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confessions ALTER COLUMN id SET DEFAULT nextval('public.confessions_id_seq'::regclass);


--
-- Name: dare_feedback id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_feedback ALTER COLUMN id SET DEFAULT nextval('public.dare_feedback_id_seq'::regclass);


--
-- Name: dare_responses id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_responses ALTER COLUMN id SET DEFAULT nextval('public.dare_responses_id_seq'::regclass);


--
-- Name: dare_submissions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_submissions ALTER COLUMN id SET DEFAULT nextval('public.dare_submissions_id_seq'::regclass);


--
-- Name: fantasy_board_reactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_board_reactions ALTER COLUMN id SET DEFAULT nextval('public.fantasy_board_reactions_id_seq'::regclass);


--
-- Name: fantasy_chat_sessions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_chat_sessions ALTER COLUMN id SET DEFAULT nextval('public.fantasy_chat_sessions_id_seq'::regclass);


--
-- Name: fantasy_chats id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_chats ALTER COLUMN id SET DEFAULT nextval('public.fantasy_chats_id_seq'::regclass);


--
-- Name: fantasy_match_notifs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_match_notifs ALTER COLUMN id SET DEFAULT nextval('public.fantasy_match_notifs_id_seq'::regclass);


--
-- Name: fantasy_match_requests id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_match_requests ALTER COLUMN id SET DEFAULT nextval('public.fantasy_match_requests_id_seq'::regclass);


--
-- Name: fantasy_matches id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_matches ALTER COLUMN id SET DEFAULT nextval('public.fantasy_matches_id_seq'::regclass);


--
-- Name: fantasy_submissions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_submissions ALTER COLUMN id SET DEFAULT nextval('public.fantasy_submissions_id_seq'::regclass);


--
-- Name: feed_comments id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_comments ALTER COLUMN id SET DEFAULT nextval('public.feed_comments_id_seq'::regclass);


--
-- Name: feed_posts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_posts ALTER COLUMN id SET DEFAULT nextval('public.feed_posts_id_seq'::regclass);


--
-- Name: friend_chats id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friend_chats ALTER COLUMN id SET DEFAULT nextval('public.friend_chats_id_seq'::regclass);


--
-- Name: friend_msg_requests id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friend_msg_requests ALTER COLUMN id SET DEFAULT nextval('public.friend_msg_requests_id_seq'::regclass);


--
-- Name: likes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.likes ALTER COLUMN id SET DEFAULT nextval('public.likes_id_seq'::regclass);


--
-- Name: maintenance_log id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.maintenance_log ALTER COLUMN id SET DEFAULT nextval('public.maintenance_log_id_seq'::regclass);


--
-- Name: miniapp_comments id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_comments ALTER COLUMN id SET DEFAULT nextval('public.miniapp_comments_id_seq'::regclass);


--
-- Name: miniapp_posts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_posts ALTER COLUMN id SET DEFAULT nextval('public.miniapp_posts_id_seq'::regclass);


--
-- Name: moderation_events id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.moderation_events ALTER COLUMN id SET DEFAULT nextval('public.moderation_events_id_seq'::regclass);


--
-- Name: muc_char_options id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_options ALTER COLUMN id SET DEFAULT nextval('public.muc_char_options_id_seq'::regclass);


--
-- Name: muc_char_questions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_questions ALTER COLUMN id SET DEFAULT nextval('public.muc_char_questions_id_seq'::regclass);


--
-- Name: muc_char_votes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_votes ALTER COLUMN id SET DEFAULT nextval('public.muc_char_votes_id_seq'::regclass);


--
-- Name: muc_characters id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_characters ALTER COLUMN id SET DEFAULT nextval('public.muc_characters_id_seq'::regclass);


--
-- Name: muc_episodes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_episodes ALTER COLUMN id SET DEFAULT nextval('public.muc_episodes_id_seq'::regclass);


--
-- Name: muc_poll_options id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_poll_options ALTER COLUMN id SET DEFAULT nextval('public.muc_poll_options_id_seq'::regclass);


--
-- Name: muc_polls id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_polls ALTER COLUMN id SET DEFAULT nextval('public.muc_polls_id_seq'::regclass);


--
-- Name: muc_series id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_series ALTER COLUMN id SET DEFAULT nextval('public.muc_series_id_seq'::regclass);


--
-- Name: muc_theories id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theories ALTER COLUMN id SET DEFAULT nextval('public.muc_theories_id_seq'::regclass);


--
-- Name: muc_theory_likes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theory_likes ALTER COLUMN id SET DEFAULT nextval('public.muc_theory_likes_id_seq'::regclass);


--
-- Name: muc_votes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_votes ALTER COLUMN id SET DEFAULT nextval('public.muc_votes_id_seq'::regclass);


--
-- Name: naughty_wyr_questions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.naughty_wyr_questions ALTER COLUMN id SET DEFAULT nextval('public.naughty_wyr_questions_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: pending_confession_replies id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_confession_replies ALTER COLUMN id SET DEFAULT nextval('public.pending_confession_replies_id_seq'::regclass);


--
-- Name: pending_confessions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_confessions ALTER COLUMN id SET DEFAULT nextval('public.pending_confessions_id_seq'::regclass);


--
-- Name: poll_options id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.poll_options ALTER COLUMN id SET DEFAULT nextval('public.poll_options_id_seq'::regclass);


--
-- Name: polls id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.polls ALTER COLUMN id SET DEFAULT nextval('public.polls_id_seq'::regclass);


--
-- Name: post_reports id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.post_reports ALTER COLUMN id SET DEFAULT nextval('public.post_reports_id_seq'::regclass);


--
-- Name: posts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.posts ALTER COLUMN id SET DEFAULT nextval('public.posts_id_seq'::regclass);


--
-- Name: profiles id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.profiles ALTER COLUMN id SET DEFAULT nextval('public.profiles_id_seq'::regclass);


--
-- Name: qa_answers id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.qa_answers ALTER COLUMN id SET DEFAULT nextval('public.qa_answers_id_seq'::regclass);


--
-- Name: qa_questions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.qa_questions ALTER COLUMN id SET DEFAULT nextval('public.qa_questions_id_seq'::regclass);


--
-- Name: reports id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports ALTER COLUMN id SET DEFAULT nextval('public.reports_id_seq'::regclass);


--
-- Name: secret_chats id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.secret_chats ALTER COLUMN id SET DEFAULT nextval('public.secret_chats_id_seq'::regclass);


--
-- Name: sensual_reactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sensual_reactions ALTER COLUMN id SET DEFAULT nextval('public.sensual_reactions_id_seq'::regclass);


--
-- Name: sensual_stories id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sensual_stories ALTER COLUMN id SET DEFAULT nextval('public.sensual_stories_id_seq'::regclass);


--
-- Name: social_comments id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_comments ALTER COLUMN id SET DEFAULT nextval('public.social_comments_id_seq'::regclass);


--
-- Name: social_friend_requests id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_friend_requests ALTER COLUMN id SET DEFAULT nextval('public.social_friend_requests_id_seq'::regclass);


--
-- Name: social_friends id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_friends ALTER COLUMN id SET DEFAULT nextval('public.social_friends_id_seq'::regclass);


--
-- Name: social_likes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_likes ALTER COLUMN id SET DEFAULT nextval('public.social_likes_id_seq'::regclass);


--
-- Name: social_posts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_posts ALTER COLUMN id SET DEFAULT nextval('public.social_posts_id_seq'::regclass);


--
-- Name: social_profiles id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_profiles ALTER COLUMN id SET DEFAULT nextval('public.social_profiles_id_seq'::regclass);


--
-- Name: stories id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.stories ALTER COLUMN id SET DEFAULT nextval('public.stories_id_seq'::regclass);


--
-- Name: story_segments id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_segments ALTER COLUMN id SET DEFAULT nextval('public.story_segments_id_seq'::regclass);


--
-- Name: story_views id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_views ALTER COLUMN id SET DEFAULT nextval('public.story_views_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: vault_categories id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_categories ALTER COLUMN id SET DEFAULT nextval('public.vault_categories_id_seq'::regclass);


--
-- Name: vault_content id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_content ALTER COLUMN id SET DEFAULT nextval('public.vault_content_id_seq'::regclass);


--
-- Name: vault_daily_category_views id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_daily_category_views ALTER COLUMN id SET DEFAULT nextval('public.vault_daily_category_views_id_seq'::regclass);


--
-- Name: vault_interactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_interactions ALTER COLUMN id SET DEFAULT nextval('public.vault_interactions_id_seq'::regclass);


--
-- Name: wyr_anonymous_users id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_anonymous_users ALTER COLUMN id SET DEFAULT nextval('public.wyr_anonymous_users_id_seq'::regclass);


--
-- Name: wyr_group_messages id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_group_messages ALTER COLUMN id SET DEFAULT nextval('public.wyr_group_messages_id_seq'::regclass);


--
-- Name: wyr_message_reactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_message_reactions ALTER COLUMN id SET DEFAULT nextval('public.wyr_message_reactions_id_seq'::regclass);


--
-- Data for Name: ad_messages; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.ad_messages (id, session_id, user_id, anon_name, msg_type, content, meta, created_at) FROM stdin;
1	4	647778438	User1	dare_done	\N	{}	2025-09-11 07:12:28.971906+00
2	5	1437934486	User2	truth	I will never give blowjob	{}	2025-09-11 08:52:53.797241+00
3	5	1437934486	User2	text	Ohh fuck of oh  yes\nI love it	{}	2025-09-11 08:54:53.820121+00
4	5	1437934486	User2	dare_done	\N	{}	2025-09-11 08:54:58.572635+00
5	5	647778438	User1	truth	Never gonna lick the pussy	{}	2025-09-11 08:55:35.338324+00
6	5	647778438	User1	text	Hows it's everyone	{}	2025-09-11 08:56:08.846072+00
7	5	647778438	User1	vote	poll	{"choice": "wild"}	2025-09-11 08:57:10.361534+00
8	5	8482725798	User3	vote	poll	{"choice": "wild"}	2025-09-11 08:57:16.45407+00
9	5	1437934486	User2	vote	poll	{"choice": "wild"}	2025-09-11 08:57:21.881256+00
10	6	647778438	User1	text	Kissing all over her body\nFrom her forehead till her toe	{}	2025-09-11 09:28:42.524688+00
11	6	647778438	User1	dare_done	\N	{}	2025-09-11 09:29:01.299109+00
\.


--
-- Data for Name: ad_participants; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.ad_participants (id, session_id, user_id, anon_name, joined_at, left_at) FROM stdin;
1	1	647778438	User1	2025-09-11 05:24:57.831221+00	\N
2	2	647778438	User1	2025-09-11 06:09:23.478388+00	\N
3	3	647778438	User1	2025-09-11 06:51:15.96867+00	\N
4	4	647778438	User1	2025-09-11 07:12:11.798965+00	\N
5	5	647778438	User1	2025-09-11 08:42:08.562872+00	\N
6	5	1437934486	User2	2025-09-11 08:52:24.671843+00	\N
7	5	8482725798	User3	2025-09-11 08:56:41.351169+00	\N
8	6	647778438	User1	2025-09-11 09:27:44.454345+00	\N
\.


--
-- Data for Name: ad_prompts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.ad_prompts (id, session_id, kind, payload, created_at) FROM stdin;
1	2	drop	{"manual": true}	2025-09-11 06:22:40.164264+00
2	2	poll	{"manual": true}	2025-09-11 06:23:10.636339+00
3	2	dare	{"manual": true}	2025-09-11 06:23:24.074119+00
4	2	dare	{"manual": true}	2025-09-11 06:23:44.783093+00
5	2	truth	{"manual": true}	2025-09-11 06:23:53.217887+00
6	2	poll	{"manual": true}	2025-09-11 06:24:03.633782+00
7	2	dare	{"manual": true}	2025-09-11 06:24:14.058133+00
8	2	poll	{"auto": true}	2025-09-11 06:25:35.13203+00
9	3	drop	{"manual": true}	2025-09-11 06:51:25.74767+00
10	3	drop	{"auto": true}	2025-09-11 06:54:24.794782+00
11	3	dare	{"auto": true}	2025-09-11 06:57:24.826388+00
12	3	poll	{"auto": true}	2025-09-11 07:00:21.919037+00
13	4	dare	{"manual": true}	2025-09-11 07:12:21.312515+00
14	4	dare	{"auto": true}	2025-09-11 07:15:20.87287+00
15	4	drop	{"auto": true}	2025-09-11 07:18:18.013943+00
16	4	poll	{"auto": true}	2025-09-11 07:21:17.982031+00
17	4	poll	{"auto": true}	2025-09-11 07:24:15.706169+00
18	4	poll	{"auto": true}	2025-09-11 07:27:20.876601+00
19	4	dare	{"auto": true}	2025-09-11 07:30:20.861783+00
20	4	poll	{"auto": true}	2025-09-11 07:33:24.347307+00
21	4	poll	{"auto": true}	2025-09-11 07:36:24.193272+00
22	4	dare	{"auto": true}	2025-09-11 07:39:24.044868+00
23	5	dare	{"text": "Share your most intense hookup story."}	2025-09-11 08:42:17.748798+00
24	5	drop	{"note": "vault"}	2025-09-11 08:45:14.478313+00
25	5	dare	{"text": "Describe your perfect one-night stand scenario step by step."}	2025-09-11 08:50:49.953051+00
26	5	truth	{"text": "Is there anything you won't do in bed?"}	2025-09-11 08:52:33.695083+00
27	5	dare	{"text": "Compose the sexiest voice message script (in text)."}	2025-09-11 08:53:47.077294+00
28	5	drop	{"note": "vault"}	2025-09-11 08:55:28.319438+00
29	5	drop	{"note": "vault"}	2025-09-11 08:56:47.069307+00
30	5	poll	{"wild": "Be dominated roughly for an hour", "sweet": "Dominate someone completely", "question": "Choose your poison..."}	2025-09-11 08:56:50.866544+00
31	5	drop	{"note": "vault"}	2025-09-11 08:58:28.326629+00
32	6	dare	{"text": "Describe your signature move that never fails."}	2025-09-11 09:28:00.940601+00
33	6	dare	{"text": "Share your most intense hookup story."}	2025-09-11 09:30:48.10906+00
34	6	dare	{"text": "Share how you'd break someone's innocence."}	2025-09-11 09:33:48.098711+00
35	6	poll	{"wild": "Smell someone's dirty clothes", "sweet": "Taste someone after they've been with someone else", "question": "Pick your perversion..."}	2025-09-11 09:36:48.104079+00
36	6	dare	{"text": "Share what you'd let someone do for money."}	2025-09-11 09:39:48.112219+00
37	6	drop	{"note": "vault"}	2025-09-11 09:42:48.101378+00
38	6	drop	{"note": "vault"}	2025-09-11 09:45:48.124028+00
39	6	drop	{"note": "vault"}	2025-09-11 09:48:48.104593+00
40	6	poll	{"wild": "Fuck in a public bathroom", "sweet": "Get fucked on a rooftop under stars", "question": "Would you rather..."}	2025-09-11 09:51:48.092542+00
41	6	drop	{"note": "vault"}	2025-09-11 09:54:48.106238+00
42	6	drop	{"note": "vault"}	2025-09-11 09:57:48.125211+00
43	6	truth	{"text": "What's the most sexually daring thing you've ever done?"}	2025-09-11 10:00:48.096887+00
44	6	truth	{"text": "If you had to pick, would you be a dominatrix or a submissive?"}	2025-09-11 10:03:48.096057+00
45	6	drop	{"note": "vault"}	2025-09-11 10:06:48.096942+00
46	6	dare	{"text": "Share what you think about your friend's partner."}	2025-09-11 10:09:48.102656+00
47	6	truth	{"text": "What's the dirtiest text you've ever sent or received?"}	2025-09-11 10:12:48.108674+00
48	6	truth	{"text": "What's the dirtiest thought you've ever had about a total stranger?"}	2025-09-11 10:15:48.113462+00
49	6	drop	{"note": "vault"}	2025-09-11 10:18:48.105518+00
\.


--
-- Data for Name: ad_sessions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.ad_sessions (id, started_at, ends_at, vibe, status) FROM stdin;
1	2025-09-11 05:24:30.622556+00	2025-09-11 05:54:30.503647+00	\N	live
2	2025-09-11 05:58:28.763916+00	2025-09-11 06:28:28.763916+00	dare	live
3	2025-09-11 06:41:48.794201+00	2025-09-11 07:11:48.794201+00	drop	live
4	2025-09-11 07:12:08.891336+00	2025-09-11 07:42:08.891336+00	dare	live
5	2025-09-11 08:42:05.703207+00	2025-09-11 09:12:05.703207+00	poll	cancelled
6	2025-09-11 09:27:41.592313+00	2025-09-11 09:57:41.592313+00	dare	live
\.


--
-- Data for Name: blocked_users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.blocked_users (user_id, blocked_uid, added_at) FROM stdin;
\.


--
-- Data for Name: chat_extensions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.chat_extensions (id, match_id, extended_by, stars_paid, minutes_added, extended_at) FROM stdin;
\.


--
-- Data for Name: chat_ratings; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.chat_ratings (id, rater_id, ratee_id, value, reason, created_at) FROM stdin;
18	1437934486	5375114177	1	\N	2025-08-29 17:19:20.76234
19	5375114177	1437934486	1	\N	2025-08-29 17:19:32.556287
29	1437934486	647778438	1	\N	2025-09-01 04:09:03.720963
30	647778438	1437934486	1	\N	2025-09-01 04:09:14.657171
31	1437934486	647778438	1	\N	2025-09-01 04:19:28.129578
32	1437934486	647778438	1	\N	2025-09-01 04:25:54.376814
33	647778438	1437934486	1	\N	2025-09-01 04:26:00.439333
34	1437934486	647778438	1	\N	2025-09-01 04:29:26.242925
35	647778438	1437934486	1	\N	2025-09-01 04:29:31.781492
36	1437934486	647778438	1	\N	2025-09-01 04:34:44.438246
37	647778438	1437934486	1	\N	2025-09-01 09:53:18.375127
38	1437934486	647778438	1	\N	2025-09-01 09:53:24.956516
39	1437934486	647778438	1	\N	2025-09-01 10:03:42.780475
40	647778438	1437934486	1	\N	2025-09-01 10:05:24.358971
41	1437934486	647778438	1	\N	2025-09-01 10:05:28.719382
42	1437934486	8482725798	1	\N	2025-09-02 07:02:06.256097
43	8482725798	1437934486	1	\N	2025-09-02 08:17:50.650063
44	647778438	1437934486	1	\N	2025-09-03 06:16:27.348162
45	1437934486	8482725798	1	\N	2025-09-06 18:17:04.380758
46	8482725798	1437934486	1	\N	2025-09-06 18:33:21.795638
47	1437934486	8482725798	-1	\N	2025-09-06 18:38:38.060936
48	8482725798	1437934486	1	\N	2025-09-06 18:50:24.850453
49	1437934486	8482725798	1	\N	2025-09-12 04:31:44.232329
50	8482725798	1437934486	1	\N	2025-09-13 07:21:42.487546
\.


--
-- Data for Name: chat_reports; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.chat_reports (id, reporter_tg_id, reported_tg_id, in_secret, text, media_file_id, media_type, created_at) FROM stdin;
18	647778438	1437934486	f	He is very good	\N	\N	2025-09-01 04:19:08.476775+00
19	647778438	1437934486	t		AgACAgUAAxkBAAIXt2i1H6kVL1PA4dVm44uPDaFGFITgAAK5wTEbgg2wVREk5Gh0IPSkAQADAgADeQADNgQ	photo	2025-09-01 04:25:07.869373+00
20	1437934486	647778438	t	He is very bad	AgACAgUAAxkBAAIZgmi1bKhUa5A-KZ60dFCvUZkxlxD_AALUxTEbtOWwVZRyjM3_eOfiAQADAgADeQADNgQ	photo	2025-09-01 09:52:32.639832+00
21	647778438	1437934486	f	He is not good	\N	\N	2025-09-01 14:18:22.178289+00
22	1437934486	647778438	f	He is fucking good	\N	\N	2025-09-01 14:18:44.906649+00
23	8482725798	1437934486	f		AgACAgUAAxkBAAIe_2i2p66oDRt1-BYEwhzl6EfjPzw9AAKqyTEbVCu4VTX-U-KAf1d1AQADAgADeQADNgQ	photo	2025-09-02 08:15:47.498935+00
24	1437934486	8482725798	f	He is not good	AgACAgUAAxkBAAI7GGi8fELwwi1Ov939uw0mD5fVRjIOAALZyTEbIz_pVVXy2iQBsDT9AQADAgADeQADNgQ	photo	2025-09-06 18:24:06.21681+00
25	8482725798	1437934486	f	He is very good	\N	\N	2025-09-06 18:38:49.8317+00
26	1437934486	8482725798	f	He is very good	\N	\N	2025-09-06 18:42:16.303762+00
27	1437934486	8482725798	f	He is very good	\N	\N	2025-09-06 18:50:37.100769+00
28	1437934486	8482725798	f	💕⚡ Find a Partner	\N	\N	2025-09-06 18:50:47.930355+00
29	1437934486	8482725798	f	He is very good	\N	\N	2025-09-06 18:55:53.666445+00
30	8482725798	1437934486	f	He is very bad	\N	\N	2025-09-06 18:57:11.779807+00
31	8482725798	1437934486	f	He is very bad nd ugly	\N	\N	2025-09-12 04:23:15.48873+00
32	8482725798	1437934486	f	He is abusing me	AgACAgUAAxkBAAJNGmjDollu4_ZQI1uUrtvnqyAq0D3MAAL1xDEbDiMgVpnQWBYYm9TQAQADAgADeQADNgQ	photo	2025-09-12 04:32:26.31787+00
33	1437934486	8482725798	f	Ajdks	AgACAgUAAxkBAAJTa2jFG7TDDDxGMnFD0_tjk2aHrGaxAAIWwzEbP7cwVtEJ-bh2yVsqAQADAgADeQADNgQ	photo	2025-09-13 07:22:29.01843+00
34	647778438	8482725798	f	Bfgi	AgACAgUAAxkBAAJTyGjFaQ_fSShEJwABVw0pn4j09LpiggAC9MUxGzPUKVYwqeiB2WVKzgEAAwIAA3kAAzYE	photo	2025-09-13 12:52:31.387222+00
35	1437934486	647778438	f	He is very bad	\N	\N	2025-09-14 05:22:25.457979+00
36	647778438	1437934486	f	Vad	AgACAgUAAxkBAAJXL2jGUSGcRNDDyH_ASHmQAs2NDR12AAK0yTEbcCkxVt9rJcGM4eHlAQADAgADeQADNgQ	photo	2025-09-14 05:22:41.573286+00
37	647778438	1437934486	t	He is bad	\N	\N	2025-09-20 07:16:40.909619+00
38	647778438	1437934486	t	He is very bad	\N	\N	2025-09-20 15:23:00.243565+00
\.


--
-- Data for Name: comment_likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.comment_likes (comment_id, user_id, created_at) FROM stdin;
8	84	2025-09-26 07:13:16.497326+00
8	2	2025-09-26 07:21:15.355354+00
8	1	2025-09-26 07:25:12.605099+00
13	1	2025-09-26 07:25:17.553136+00
20	2	2025-09-26 10:20:14.889512+00
\.


--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.comments (id, post_id, user_id, text, created_at, pinned, pinned_at, pinned_by_user_id, profile_id) FROM stdin;
8	5	1	Waah kya baat hai bhai maza aa gaya	2025-09-25 14:40:46.633121	f	\N	\N	\N
13	5	84	Sab mast hai udar to	2025-09-25 14:59:45.472782	f	\N	\N	\N
14	1	1	Test comment from API	2025-09-26 05:10:39.310174	f	\N	\N	\N
15	1	2	TESTING FIX - Comment from post owner 1437934486	2025-09-26 05:21:04.386512	f	\N	\N	\N
17	4	2	So good so nice	2025-09-26 07:22:06.634892	f	\N	\N	\N
18	5	84	So good	2025-09-26 09:04:18.141049	f	\N	\N	\N
19	5	2	Jai hooooo	2025-09-26 09:26:43.195162	f	\N	\N	\N
20	5	2	Sahi h bhai	2025-09-26 10:19:48.389175	f	\N	\N	\N
21	1	1	Waaah bhai mauz kardi	2025-09-26 10:40:29.047979	f	\N	\N	\N
22	1	1	Kya baat kya baat	2025-09-26 10:49:31.871513	f	\N	\N	\N
23	6	84	Http 200	2025-09-26 10:51:14.470718	f	\N	\N	\N
24	7	1	Aaya kya notification 🤣	2025-09-26 11:03:40.709338	f	\N	\N	\N
25	8	1	Comment me	2025-09-26 11:21:58.343751	f	\N	\N	\N
26	9	2	Ganpati bappa morya 💖	2025-09-26 11:54:19.297956	f	\N	\N	\N
27	11	1	Failed mission	2025-09-26 13:25:47.938454	f	\N	\N	\N
28	6	84	Kya kya bataya h	2025-09-26 13:50:23.923146	f	\N	\N	\N
29	5	84	Waah bhai waah kya baat hai	2025-09-26 14:10:51.161075	f	\N	\N	\N
30	11	1	So niceeeee	2025-09-26 14:25:38.568699	f	\N	\N	\N
31	6	84	Woww so beautiful	2025-09-26 14:26:41.448877	f	\N	\N	\N
32	11	2	Maza aa gaya bhidu	2025-09-26 14:47:10.124015	f	\N	\N	\N
33	10	2	Mission failed	2025-09-26 15:03:41.078367	f	\N	\N	\N
34	13	2	Hmm nice	2025-09-28 12:16:13.619226	f	\N	\N	\N
35	17	1	Hmm nice	2025-09-28 15:09:50.290839	f	\N	\N	\N
36	17	1	Ohh yesss	2025-09-28 15:49:13.048745	f	\N	\N	\N
37	16	2	Hmm nice	2025-09-28 16:05:31.702208	f	\N	\N	\N
38	17	1	Hmm okay got it	\N	f	\N	\N	\N
39	17	1	Hmm okay got it	\N	f	\N	\N	\N
40	17	1	Kya baat hai bhai	2025-09-29 04:38:09.581252	f	\N	\N	\N
41	17	1	Sahi hai bhai	2025-09-29 05:03:22.923208	f	\N	\N	\N
42	17	1	Waaha kajsjsoeoor	2025-09-29 05:04:38.85948	f	\N	\N	\N
43	17	1	Waah my god	2025-09-29 05:16:59.519311	f	\N	\N	1
44	39	1	Jai hind🇮🇳	2025-09-29 09:47:52.20587	f	\N	\N	1
45	39	1	Kya kya baat hai	2025-09-29 10:02:55.315297	f	\N	\N	1
46	39	1	Goal	2025-09-29 10:12:41.721063	f	\N	\N	1
47	39	1	Jai hind ki sena🇮🇳🇮🇳	2025-09-29 10:20:32.344335	f	\N	\N	1
48	37	2	Wttiipop	2025-09-29 11:05:58.265089	f	\N	\N	3
49	37	2	Wyooopp	2025-09-29 11:16:13.835512	f	\N	\N	3
50	39	1	Ohhhhhhhh niceeeee	2025-09-29 11:35:26.951854	f	\N	\N	1
51	37	2	Ohhh lala	2025-09-29 11:36:50.573222	f	\N	\N	3
52	39	1	Ajskskskskalelel	2025-09-29 11:56:36.041035	f	\N	\N	1
53	37	2	Jajsjkwoowowwp	2025-09-29 14:59:08.428796	f	\N	\N	3
\.


--
-- Data for Name: confession_deliveries; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confession_deliveries (id, confession_id, user_id, delivered_at) FROM stdin;
77	66	647778438	2025-09-12 14:00:04.721187+00
78	80	647778438	2025-09-12 14:00:04.751634+00
79	68	8482725798	2025-09-12 14:00:06.081158+00
80	71	8482725798	2025-09-12 14:00:06.109754+00
81	73	1437934486	2025-09-12 14:00:07.437889+00
82	71	1437934486	2025-09-12 14:00:07.483171+00
83	57	647778438	2025-09-12 16:09:14.983667+00
84	60	8482725798	2025-09-12 16:09:16.338031+00
85	61	1437934486	2025-09-12 16:09:17.702911+00
86	77	647778438	2025-09-12 16:12:15.103163+00
87	69	8482725798	2025-09-12 16:12:16.708212+00
88	60	1437934486	2025-09-12 16:12:18.227473+00
89	78	1437934486	2025-09-12 16:34:55.685503+00
90	61	8482725798	2025-09-12 16:34:57.029642+00
91	60	647778438	2025-09-12 16:34:58.371949+00
92	57	1437934486	2025-09-12 16:37:55.584896+00
93	59	8482725798	2025-09-12 16:37:56.914339+00
94	81	647778438	2025-09-12 16:37:58.31363+00
95	72	1437934486	2025-09-12 16:54:26.689306+00
96	80	8482725798	2025-09-12 16:54:28.047757+00
97	62	647778438	2025-09-12 16:54:29.385257+00
98	81	1437934486	2025-09-12 16:57:27.136378+00
99	64	8482725798	2025-09-12 16:57:28.503591+00
100	72	647778438	2025-09-12 16:57:29.928557+00
101	79	1437934486	2025-09-12 17:12:38.334044+00
102	67	8482725798	2025-09-12 17:12:39.678564+00
103	69	647778438	2025-09-12 17:12:41.048226+00
104	63	1437934486	2025-09-12 17:15:38.265989+00
105	70	8482725798	2025-09-12 17:15:39.670868+00
106	59	647778438	2025-09-12 17:15:40.996595+00
107	75	1437934486	2025-09-12 17:50:34.654224+00
108	65	8482725798	2025-09-12 17:50:35.981982+00
109	74	647778438	2025-09-12 17:50:37.303017+00
110	69	1437934486	2025-09-12 17:53:34.513362+00
111	73	8482725798	2025-09-12 17:53:35.837132+00
112	63	647778438	2025-09-12 17:53:37.167214+00
113	64	1437934486	2025-09-12 18:04:07.494688+00
114	76	8482725798	2025-09-12 18:04:08.91333+00
115	78	647778438	2025-09-12 18:04:10.254752+00
116	58	1437934486	2025-09-12 18:07:07.447396+00
117	79	8482725798	2025-09-12 18:07:08.779827+00
118	75	647778438	2025-09-12 18:07:10.123816+00
119	71	647778438	2025-09-13 04:54:21.743047+00
120	62	8482725798	2025-09-13 04:54:23.102056+00
121	76	1437934486	2025-09-13 04:54:24.453148+00
122	68	647778438	2025-09-13 04:57:21.793303+00
123	74	8482725798	2025-09-13 04:57:23.155938+00
124	70	1437934486	2025-09-13 04:57:24.507709+00
125	67	1437934486	2025-09-13 14:00:10.065693+00
126	58	8482725798	2025-09-13 14:00:11.505612+00
127	65	647778438	2025-09-13 14:00:12.931372+00
128	81	1040560837	2025-09-15 14:00:05.705658+00
129	66	1437934486	2025-09-15 14:00:07.113946+00
130	77	8482725798	2025-09-15 14:00:08.452816+00
131	52	647778438	2025-09-15 14:00:09.800555+00
\.


--
-- Data for Name: confession_leaderboard; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confession_leaderboard (id, user_id, period, confession_count, total_reactions_received, replies_received, rank_type, rank_position, updated_at) FROM stdin;
\.


--
-- Data for Name: confession_mutes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confession_mutes (user_id, confession_id, created_at) FROM stdin;
1437934486	65	2025-09-12 17:51:23.352816+00
\.


--
-- Data for Name: confession_reactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confession_reactions (id, confession_id, user_id, reaction_type, created_at, approved, approved_at) FROM stdin;
1	21	647778438	love	2025-09-07 08:34:17.665435+00	f	\N
2	23	647778438	love	2025-09-07 08:43:46.3635+00	f	\N
3	17	647778438	love	2025-09-07 09:13:22.918184+00	f	\N
4	44	8482725798	love	2025-09-07 11:03:30.502624+00	f	\N
5	45	8482725798	love	2025-09-07 11:36:17.233856+00	f	\N
6	80	647778438	love	2025-09-12 14:02:18.692668+00	f	\N
7	68	8482725798	love	2025-09-12 14:23:03.203467+00	f	\N
8	66	647778438	love	2025-09-12 15:11:12.522654+00	f	\N
10	68	8482725798	wow	2025-09-12 15:12:18.435341+00	f	\N
11	66	647778438	wow	2025-09-12 15:36:15.380853+00	f	\N
12	60	8482725798	love	2025-09-12 16:09:28.024211+00	f	\N
13	57	647778438	love	2025-09-12 16:09:41.44838+00	f	\N
14	77	647778438	love	2025-09-12 16:31:30.20369+00	t	2025-09-12 16:31:30.20369+00
15	60	647778438	love	2025-09-12 16:35:37.822738+00	t	2025-09-12 16:35:37.822738+00
16	72	1437934486	love	2025-09-12 16:55:06.888068+00	t	2025-09-12 16:55:06.888068+00
17	72	1437934486	laugh	2025-09-12 16:57:09.215561+00	t	2025-09-12 16:57:09.215561+00
18	79	1437934486	love	2025-09-12 17:13:21.350263+00	t	2025-09-12 17:13:21.350263+00
19	65	8482725798	love	2025-09-12 17:50:46.200077+00	t	2025-09-12 17:50:46.200077+00
20	64	1437934486	love	2025-09-12 18:04:20.184364+00	t	2025-09-12 18:04:20.184364+00
21	58	1437934486	love	2025-09-13 03:54:12.241488+00	t	2025-09-13 03:54:12.241488+00
22	70	1437934486	love	2025-09-13 05:00:39.207266+00	t	2025-09-13 05:00:39.207266+00
23	74	8482725798	love	2025-09-13 05:09:19.475589+00	t	2025-09-13 05:09:19.475589+00
24	58	8482725798	love	2025-09-13 14:01:58.539448+00	t	2025-09-13 14:01:58.539448+00
25	52	647778438	love	2025-09-15 14:15:31.766591+00	t	2025-09-15 14:15:31.766591+00
26	77	8482725798	love	2025-09-15 14:43:52.38764+00	t	2025-09-15 14:43:52.38764+00
27	77	8482725798	wow	2025-09-15 14:54:27.620207+00	t	2025-09-15 14:54:27.620207+00
28	66	1437934486	love	2025-09-15 14:59:38.821487+00	t	2025-09-15 14:59:38.821487+00
29	66	1437934486	sad	2025-09-15 15:04:05.551922+00	t	2025-09-15 15:04:05.551922+00
\.


--
-- Data for Name: confession_replies; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confession_replies (id, original_confession_id, replier_user_id, reply_text, created_at, reply_reactions, is_anonymous, approved, approved_at) FROM stdin;
1	34	8482725798	I am also get this same feeling	2025-09-07 08:18:25.007223+00	0	t	f	\N
2	10	8482725798	this is so good and nice \nKeep going	2025-09-07 08:20:17.738468+00	0	t	f	\N
3	18	647778438	I am also like this bro	2025-09-07 08:20:57.131102+00	0	t	f	\N
4	23	647778438	this is so nice bro\nI am with you	2025-09-07 08:44:12.992243+00	0	t	f	\N
5	44	8482725798	Ganpati bappa morya 💖	2025-09-07 11:04:00.190292+00	0	t	f	\N
6	46	8482725798	This is so good and nice\n\nLoved it💖	2025-09-07 11:47:15.475062+00	0	t	f	\N
7	47	647778438	So nice	2025-09-07 13:10:19.312766+00	0	t	f	\N
8	68	8482725798	Sahi hai bhai ekdum kadak	2025-09-12 14:25:03.234688+00	0	t	f	\N
9	66	647778438	Kya bata hai bhai mazedar	2025-09-12 15:10:31.678988+00	0	t	f	\N
17	57	647778438	Kya baat hai bhai\n\nMaza aa gaya	2025-09-12 16:10:06.144466+00	0	t	f	\N
18	61	8482725798	Kya bata akdksla	2025-09-12 16:36:05.552508+00	0	t	t	2025-09-12 16:36:05.552508+00
19	72	8482725798	Thanx for the like	2025-09-12 16:55:39.61722+00	0	t	t	2025-09-12 16:55:39.61722+00
20	65	8482725798	Hehe so good	2025-09-12 17:51:16.318123+00	0	t	t	2025-09-12 17:51:16.318123+00
21	65	1437934486	Hehe thanx	2025-09-12 17:52:33.45133+00	0	t	t	2025-09-12 17:52:33.45133+00
22	64	1437934486	Mazedar	2025-09-12 18:05:05.737563+00	0	t	t	2025-09-12 18:05:05.737563+00
23	58	1437934486	So good	2025-09-13 03:55:16.861073+00	0	t	t	2025-09-13 03:55:16.861073+00
24	70	1437934486	Sahi hai bhai	2025-09-13 05:01:14.125874+00	0	t	t	2025-09-13 05:01:14.125874+00
25	58	8482725798	Damn this is so good	2025-09-13 14:02:39.285779+00	0	t	t	2025-09-13 14:02:39.285779+00
26	52	647778438	Sahi j	2025-09-15 14:17:05.398781+00	0	t	t	2025-09-15 14:17:05.398781+00
28	77	8482725798	Haaye kya baat h	2025-09-15 14:43:26.950027+00	0	t	t	2025-09-15 14:43:26.950027+00
30	66	1437934486	Sahi h	2025-09-15 14:59:49.828964+00	0	t	t	2025-09-15 14:59:49.828964+00
\.


--
-- Data for Name: confession_stats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confession_stats (user_id, total_confessions, weekly_confessions, current_streak, longest_streak, total_reactions_received, total_replies_received, best_confessor_score, last_confession_date, created_at, updated_at) FROM stdin;
1437934486	4	4	1	1	4	4	0	2025-09-12	2025-09-07 11:57:47.213102+00	2025-09-12 10:27:35.89286+00
647778438	14	14	1	2	7	7	0	2025-09-20	2025-09-07 06:49:39.51857+00	2025-09-20 02:28:17.592694+00
8482725798	8	8	1	2	6	3	0	2025-09-27	2025-09-07 08:25:54.798128+00	2025-09-27 13:42:03.037442+00
\.


--
-- Data for Name: confessions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.confessions (id, author_id, text, created_at, delivered, delivered_at, delivered_to, system_seed, deleted_at) FROM stdin;
48	647778438	I secretly love being called degrading names during sex and it makes me come instantly. When someone calls me their dirty slut or tells me I'm a good little whore, I lose complete control. There's something about that contrast - being treated like a goddess outside the bedroom but degraded during sex - that drives me wild. I love when they grab my face and make me repeat back how much of a slut I am for them. The dirtier the talk, the wetter I get. Sometimes I beg them to humiliate me more, to treat me like their personal fucktoy. I know it sounds terrible but being objectified in that moment makes me feel incredibly powerful and sexy. I've never told anyone how much I crave this because I'm afraid they'll judge me, but it's become essential to my sexual satisfaction.	2025-09-12 10:08:10.519066+00	f	\N	\N	f	\N
49	8482725798	I had an affair with someone much younger and it was the hottest sex of my life. He was so eager and enthusiastic, worshipping my body like I was a goddess. His inexperience was actually a turn-on because I got to teach him exactly how to please me. The age gap made everything feel forbidden and exciting. He would text me throughout the day about what he wanted to do to me, getting more confident and dirty as time went on. When we finally had sex, he couldn't get enough of me - going down on me for what felt like hours. His stamina was incredible; we fucked multiple times in one night. He made me feel young and desirable again. Even though it's over now, I still touch myself thinking about his enthusiastic mouth and hands all over my body.	2025-09-12 10:11:40.534092+00	f	\N	\N	f	\N
50	1437934486	I'm secretly bi-curious and can't stop thinking about being with another woman. I've always been attracted to men, but lately I find myself staring at women's lips, imagining what it would feel like to kiss them. I fantasize about soft skin, gentle touches, and learning how to please a woman's body. Sometimes I watch lesbian porn and imagine myself in those scenarios. I want to know what it feels like to have someone who understands my body pleasure me. The thought of 69ing with another woman makes me incredibly wet. I'm terrified but excited about the possibility of exploring this side of myself. I've been flirting with women online but haven't worked up the courage to meet anyone yet. This secret desire is consuming my thoughts.	2025-09-12 10:15:21.586219+00	f	\N	\N	f	\N
51	647778438	I have an addiction to sexting with strangers online. There's something thrilling about describing my fantasies to someone I've never met. I love building up the tension through messages, getting more and more explicit until we're both desperately turned on. Sometimes I'll send teasing photos - just enough to drive them wild but leaving them wanting more.\nThe best conversations are when we create elaborate scenarios together, taking turns describing what we'd do to each other. I've had some of my most intense orgasms while reading their dirty messages and touching myself. My partner has no idea about this secret side of me. The anonymous nature makes me feel free to explore fantasies I'd never admit to in real life.	2025-09-12 10:20:45.350542+00	f	\N	\N	f	\N
52	8482725798	I discovered I love being dominated and now I crave it constantly. My first experience with bondage and rough play awakened something primal in me. Being tied up, blindfolded, and completely at someone's mercy was the most intense sexual experience of my life. I love when they pull my hair, spank me hard, and tell me exactly what to do. The mix of pain and pleasure drives me wild. Now vanilla sex feels boring  I need that edge, that power exchange. I want to be their little slut, used for their pleasure. Sometimes I beg them to be rougher, to push my limits. The marks they leave on my body are like trophies. I've never felt more sexually alive than when I'm completely surrendering control.	2025-09-12 10:22:51.469493+00	f	\N	\N	f	\N
53	1437934486	I'm completely obsessed with my boss and it's driving me crazy. He is so confident and commanding in meetings that I imagine him dominating me in bed. When he lean over my desk to look at my work, his cologne makes me dizzy with lust. I've started wearing shorter skirts and lower-cut tops hoping he will notice me. Sometimes I catch him looking and wonder if he is thinking the same dirty thoughts I am. I fantasize about staying late at the office and him bending me over my desk, pulling my hair while he fuck me hard. Or being called into his office and dropping to my knees to pleasure him. The power dynamic makes it even hotter. I touch myself thinking about him every single night.	2025-09-12 10:25:47.556434+00	f	\N	\N	f	\N
54	647778438	I had a one-night stand that turned into the most mind blowing sex of my life. We met at a bar and the chemistry was instant  the way he looked at me made me wet before we even spoke. We barely made it to his apartment before we were tearing each other's clothes off. He pushed me against the door and kissed me so hard I thought I might faint. When he went down on me, I came so hard my legs were shaking. But the best part was when he whispered all the dirty things he wanted to do to me while he fucking me senseless. We went at it for hours in every position imaginable. I've never felt so satisfied and exhausted at the same time. I still get turned on just thinking about that night.	2025-09-12 10:29:20.082142+00	f	\N	\N	f	\N
55	647778438	I'm addicted to risky public sex and the thrill of almost getting caught. My partner and I have fucked in bathroom stalls, empty conference rooms, and once even in a secluded spot at the beach during sunset. The adrenaline rush of potentially being discovered makes every sensation more intense. Last week we had sex in a parking garage late at night - I was bent over the hood of the car moaning so loud I was sure someone would hear. The danger makes me come harder than ever before. Sometimes we'll start fooling around in semi-public places just to see how far we can go before we have to stop. I love the way my partner's eyes light up when I suggest somewhere new and risky. Normal bedroom sex feels tame compared to the excitement of public encounters.	2025-09-12 10:53:01.07345+00	f	\N	\N	f	\N
56	647778438	I've been having the most intense fantasies about my neighbor. Every morning when I see him through my window, I imagine what it would be like to pin him against the wall and kiss him passionately. The way he move, the way he bite his lip when he is thinking - it drives me absolutely wild. Last week he asked to borrow sugar and I could barely contain myself. When our hands touched passing the container, I felt electricity shoot through my entire body. I spent the rest of the day imagining those hands all over me. I know it's wrong but I can't stop thinking about him naked in my bed, moaning my name. Sometimes I touch myself thinking about him and it's the most intense orgasm I've ever had.	2025-09-12 10:55:23.310294+00	f	\N	\N	f	\N
57	8482725798	I wake up every morning and the first thing I do is check my phone to see if anyone texted me overnight. When there are no messages, I feel this weird emptiness in my chest. Then I scroll through Instagram stories of people having fun, traveling, being in relationships, and I compare my boring life to their highlight reels. I get ready for work while listening to the same sad playlist I've had for months. At the office, I pretend to be busy and social, but during lunch breaks I sit alone scrolling through social media or reading random articles. I come home to an empty apartment, order food online, and binge-watch Netflix shows until I fall asleep. On weekends, I stay in bed until noon, then feel guilty about wasting the day. I keep telling myself I'll start a hobby, join a gym, make new friends, but Sunday evening comes and I realize I spent another weekend doing nothing productive. Sometimes I video call my family and act like everything is great, but I can't tell them how lonely I actually feel. Before sleeping, I scroll through my phone one more time hoping for some notification that never comes.	2025-09-12 11:20:37.067903+00	f	\N	\N	t	\N
58	647778438	Har subah jab main apne phone ki alarm se uthti hun, toh sabse pehle main WhatsApp check karti hun ki kisi ne message kiya hai ya nahi. Aur jab koi message nahi hota, toh dil mein ek ajeeb sa khaalipan sa lagta hai. Fir main apne ex ke last seen check karti hun, even though humne 6 mahine pehle break up kiya hai. Main jaanti hun ye galat hai, but somehow uska online hona mujhe lagta hai ki life normal chal rahi hai. Office jaane se pehle main mirror mein khud ko dekhti hun aur sochti hun ki kaash koi aisa ho jo mujhe bataye ki main aaj beautiful lag rahi hun. Lunch break mein main akele cafeteria mein baithkar Instagram stories dekhti rehti hun, sabke happy moments dekh kar khud ko compare karti hun. Shaam ko ghar aake main apni mummy se phone pe baat karti hun, but unhe ye nahi bata sakti ki main kitna lonely feel kar rahi hun. Raat ko sone se pehle main diary likhti hun, woh bhi sirf phone ke notes mein, ki kaash kal kuch acha ho.	2025-09-12 11:20:37.067903+00	f	\N	\N	t	\N
59	1437934486	I'm 28 and I still don't feel like a real adult. I go to work every day, pay my bills, and act responsible, but inside I feel like I'm just pretending to know what I'm doing. When my friends talk about mortgages, marriage plans, and career goals, I nod along but honestly I have no idea where my life is heading. I still eat cereal for dinner sometimes and my idea of cleaning is shoving everything in a closet. I watch YouTube videos about how to be a successful man and 10 habits of millionaires but never actually implement anything. Dating feels impossible because I don't even know who I am, how can I present myself to someone else? I lie to my parents about how well I'm doing because I don't want them to worry. On weekends I play video games for hours and feel guilty about not being more productive. I see guys my age getting engaged, buying houses, getting promoted, and I wonder if there's something wrong with me. Sometimes I think I peaked in college and this is just what adult life feels like - going through the motions without real purpose or excitement.	2025-09-12 11:20:37.067903+00	f	\N	\N	t	\N
60	8482725798	Yaar main tumhe sach batau toh main bilkul lost hun life mein. Office jaata hun, kaam karta hun, paisa kamata hun, but mujhe lagta hai ki main sirf robot ki tarah function kar raha hun. Subah uthta hun toh motivation nahi hoti, bas alarm sun kar majboori mein uthna padta hai. Office mein colleagues se hassi mazak karta hun, but andar se main khali feel karta hun. Lunch break mein main akele baithta hun aur phone mein timepass karta hun because kisi se genuine conversation nahi kar sakta. Ghar aata hun toh parents puchte hain kaise gya din, main accha tha bol deta hun but actually main bore ho chuka hun routine se. Weekend pe friends plans banate hain but main excuse banata hun because energy nahi hoti socialize karne ki. Main YouTube pe motivational videos dekhta hun, self-help books padhta hun, but koi real change nahi aaya life mein. Sometimes main sochta hun ki maybe main depression mein hun, but therapy lene se darr lagta hai ki society kya sochegi. Raat ko late tak jaagta hun phone mein scroll karte hue because sleep bhi nahi aati anxiety se. Mujhe lagta hai main apne potential waste kar raha hun but nahi pata kaise change karun.	2025-09-12 11:20:37.067903+00	f	\N	\N	t	\N
61	647778438	I work in corporate but I feel like I'm living a double life. During the day I'm professional, attend meetings, give presentations, and network with colleagues. But as soon as I get home, I change into old pajamas and watch reality TV shows that I would never admit to watching. I have this Pinterest board full of aesthetic lifestyle goals - minimalist apartments, healthy meals, workout routines, reading lists - but my actual life is messy, chaotic, and nothing like what I project online. I buy expensive skincare products thinking they'll make me feel more put-together, but I still feel insecure about everything. My social media shows carefully curated photos of brunch dates and work achievements, but I don't post about staying in bed all weekend or crying during random commercials. I have these conversations with coworkers about career ambitions and five-year plans, but honestly I'm just trying to make it through each day without having a breakdown. I keep waiting for the moment when I'll feel like I have my life figured out, but every year I realize I'm still the same confused person just with more responsibilities.	2025-09-12 11:20:37.067903+00	f	\N	\N	t	\N
62	1437934486	I've been in love with my best friend for three years and it's slowly killing me inside. We talk every day, share everything, and she tells me I'm the only person who truly understands her. But whenever I try to hint at something more, she changes the subject or talks about how grateful she is to have me as a friend. I've watched her date other guys who treat her badly, and every time she comes crying to me about how men are trash. I comfort her, give her advice, and secretly hope she'll realize I'm different. I've tried dating other girls to get over her, but I always end up comparing them to her. She hugs me, texts me good morning every day, and calls me when she can't sleep, but I know she'll never see me romantically. Last month she asked me to help her pick out an outfit for a date with some new guy, and I smiled and helped her while dying inside. I know I should distance myself for my own mental health, but I can't imagine my life without her in it. I'm stuck in this endless cycle of hope and disappointment, and I don't know how to break free without losing the most important person in my life.	2025-09-12 11:21:36.035632+00	f	\N	\N	t	\N
63	8482725798	I dated someone for two years who never officially called me his girlfriend but acted like I was when it was convenient for him. He would text me every day, take me on dates, introduce me to his friends, and even brought me to family gatherings. But whenever I brought up our relationship status, he'd say things like why do we need labels or let's just enjoy what we have. I convinced myself that labels didn't matter because our connection felt real. I turned down other guys who were interested because I thought what we had was special and worth waiting for. Then I found out through social media that he's now in an official relationship with someone else, posting couple photos and calling her his girlfriend. I felt like such an idiot for believing his excuses for two years. Looking back, I realize he was keeping me as an option while looking for someone he actually wanted to commit to. I gave him all the benefits of a relationship without any of the commitment, and he took advantage of my feelings. Now I can't trust anyone who says they're not ready for a relationship, and I question every romantic situation wondering if I'm being used again.	2025-09-12 11:21:36.035632+00	f	\N	\N	t	\N
64	647778438	My ex broke up with me eight months ago saying she needed space to figure herself out, and I'm still not over it even though she's clearly moved on. We dated for three years and I thought we were going to get married. She said she felt overwhelmed by the pressure and needed time to be alone and grow as a person. I respected her decision and gave her space, thinking maybe she'd realize what we had was worth fighting for. But now I see her on social media traveling with new friends, starting a new job, and looking happier than she ever did with me. She's become this whole new person that I don't recognize, and it hurts to realize that maybe I was holding her back from becoming who she wanted to be. I keep replaying our last conversations wondering if there were signs I missed or things I could have done differently. I've tried dating other people but it feels forced and unfair to them because I'm still comparing everyone to her. The worst part is seeing how much better her life seems without me in it, and wondering if I'll ever find someone who fits with me the way I thought she did.	2025-09-12 11:21:36.035632+00	f	\N	\N	t	\N
65	1437934486	Main apne college ke senior se teen saal tak one-sided pyaar karti rahi jo mujhe kabhi pata hi nahi chala ki woh kya feel karta hai mere baare mein. Woh popular tha, good looking tha, aur bahut saari ladkiyan uske peeche thi, but somehow hum close dost ban gaye. Main usse daily messages karti thi, uske problems sun kar solutions deti thi, uske mood swings handle karti thi, but kabhi hint nahi diya ki main usse pyaar karti hun. Jab woh kisi aur ladki ke saath date pe jaata tha, main smile kar kar advice deti thi but andar se mar jaati thi. Main uski har photo pe like karti thi, uske stories pe react karti thi, uske friends se acchi tarah se baat karti thi hoping ki shayad koi chance mile. College ke last year main finally confess kiya because lagta tha ki ab ya kabhi nahi. But usne mujhse kaha ki I really care about you as a friend, but I never thought of you that way. Graduation ke baad woh dusre city chala gaya aur ab main dekh rahi hun ki woh kisi aur se serious relationship mein hai. Main abhi bhi usse compare karti hun every guy se jo milta hai, aur koi match nahi karta. Mujhe regret hai ki main itne saal waste kiye ek person pe jo mujhe kabhi romantically dekha hi nahi.	2025-09-12 11:21:36.035632+00	f	\N	\N	t	\N
66	8482725798	Yaar meri pehli girlfriend ne mujhe 5 saal pehle choda tha family pressure mein, aur main abhi bhi usse completely bhul nahi paya hun. College love tha, pure tha, innocent tha. Humne future plans banaye the, main uske ghar jaata tha, uske parents mujhe achha lagte the. But shaadi ke time uske family ne kaha ki main different caste se hun aur ye relationship possible nahi hai. Usne try kiya convince karne ka, but ultimately family choose kiya love ke upar. Last time jab hum mile the, dono ro rahe the aur kehte rahe ki kash kuch aur kar sakte. Ab woh married hai, bachcha bhi hai, settled life hai. Main bhi kisi aur se relationship mein hun, good girl hai, family approve karti hai, but woh feeling kabhi nahi aayi jo pehli wali ke saath thi. Sometimes main guilty feel karta hun ki present girlfriend ke saath fair nahi kar raha because comparison hamesha chalta rehta hai. Main social media pe uski photos dekh leta hun kabhi kabhi, aur wonder karta hun ki agar us time main financially stable hota, ya different approach kiya hota family ko convince karne ka, toh kya story different hoti. But ab sirf regret hai aur what-ifs ke sawal hain jo kabhi answer nahi milenge.	2025-09-12 11:21:36.035632+00	f	\N	\N	t	\N
67	647778438	I have to confess that I'm completely obsessed with celebrity gossip and reality TV, even though I present myself as someone who's into intellectual content. I spend hours reading celebrity blind items, watching reaction videos to reality show episodes, and following drama on social media. I subscribe to all the gossip channels on YouTube and know way too much about celebrities' personal lives. When my friends ask what I've been watching, I mention documentaries or art films, but the truth is I binge-watch The Bachelor, Love Island, and Keeping Up with the Kardashians. I get emotionally invested in these strangers' lives and genuinely care about who gets eliminated or who's dating whom. I know it's superficial and probably not the best use of my time, but it's my escape from real life stress. There's something comforting about caring about problems that aren't actually mine. I've tried to get into more respectable entertainment, but nothing gives me the same instant gratification as celebrity drama. I feel like I'm living a double life - intellectual by day, reality TV consumer by night.	2025-09-12 11:22:30.489737+00	f	\N	\N	t	\N
68	1437934486	Bhai main tumhe ek baat batau jo kisi ko nahi pata - main Korean dramas dekhta hun aur unpe emotional ho jaata hun. Meri friends ko lagta hai main sirf action movies aur sports dekhta hun, but ghar pe main K-dramas binge watch karta hun. Goblin, Crash Landing on You, Descendants of the Sun - main sabko dekha hai aur har episode mein cry karta hun. Main Korean culture research karta hun, Korean food try karta hun, even BTS ke songs sunte hun. Agar meri buddies ko pata chale toh mera mazaak udayenge, unko lagta hai ye sab girly content hai. But honestly main Western shows se zyada Korean content enjoy karta hun because emotions genuine lagte hain aur storytelling different hai. Main secretly Korean language seekhne ki koshish kar raha hun, Korean skincare routine follow karta hun. Sometimes main K-pop concerts ka videos dekhta hun aur wish karta hun ki India mein bhi aaye. Mujhe pata hai stereotypical hai ki guys ye sab nahi karte, but main guilty feel nahi karna chahta isse enjoy karne mein. Korean content ne mujhe zyada emotional aur sensitive banaya hai, aur main isse positive change maanta hun.	2025-09-12 11:22:30.489737+00	f	\N	\N	t	\N
69	8482725798	I have this secret obsession with cooking shows and I spend my weekends creating elaborate meals just for myself, even though my friends think I survive on takeout and instant noodles. I watch every season of MasterChef, Chef's Table, and Gordon Ramsay's shows religiously. I get emotional watching people achieve their culinary dreams and I've actually cried during some cooking competition finales. I've invested in expensive kitchen equipment, collect cookbooks, and know way more about food than anyone expects from a single guy in his twenties. I go to farmers markets alone, experiment with international cuisines, and take photos of my dishes even though I never post them because I'm worried about what people would think. When my friends come over, I downplay my cooking skills and just order pizza to maintain my typical bachelor image. But honestly, cooking is like meditation for me - it's the only time I feel truly creative and accomplished. I dream of maybe taking professional cooking classes or even opening a small restaurant someday, but I'm scared of the stereotype that men who love cooking are somehow less masculine.	2025-09-12 11:22:30.489737+00	f	\N	\N	t	\N
70	647778438	Main ek weird confession karna chahti hun - main horror content aur paranormal theories pe completely addicted hun even though main normally rational person hun. Main raat ko 2-3 baje tak YouTube pe ghost videos, alien conspiracy theories, unsolved mysteries dekhti hun. Main horror podcasts sunti hun while working, true crime documentaries binge watch karti hun. Meri friends ko lagta hai main logical aur scientific minded hun, but secretly main tarot card reading videos dekhti hun, astrology mein believe karti hun, numerology try karti hun. Main psychic reading sessions attend karti hun secretly, crystals collect karti hun, sage burning try karti hun. Jab scary incident hota hai news mein, main hours spend karti hun alternative theories research karne mein. Main Reddit pe conspiracy subreddits follow karti hun, paranormal investigation channels subscribe karti hun. Mujhe pata hai scientifically ye sab questionable hai, but mujhe thrill milta hai unknown explore karne mein. Day time main logical discussions kar sakti hun, but personally main supernatural possibilities mein believe karti hun. Ye mera guilty pleasure hai because intellectually main skeptical hun but emotionally main mystery aur magic chahti hun life mein.	2025-09-12 11:22:30.489737+00	f	\N	\N	t	\N
71	1437934486	I'm secretly addicted to romance novels and fanfiction, and I've created this whole elaborate fantasy life around fictional characters. I read multiple books a week, mostly cheesy romance with predictable plots - CEO romances, enemies to lovers, fake dating scenarios. I have Kindle Unlimited just so I can binge-read without judgment from bookstore clerks. I've even started writing my own fanfiction under a pseudonym and have gained a small following online. When book clubs discuss literary fiction, I participate and act interested, but I'd much rather be reading about some billionaire falling for his assistant. I spend hours on Goodreads reading reviews, creating lists, and joining groups dedicated to specific romance tropes. I know it's escapist and probably giving me unrealistic expectations about relationships, but these stories make me happy in a way that serious literature never does. I've decorated my apartment with books that make me look intellectual, but my actual reading consists of stories where the main characters always get their happily ever after. It's embarrassing to admit, but fictional love stories bring me more joy than most real-life experiences.	2025-09-12 11:22:30.489737+00	f	\N	\N	t	\N
72	8482725798	My biggest life goal is to start a nonprofit organization that provides free mental health resources to men, especially in communities where seeking help is stigmatized. I've struggled with depression and anxiety for years but was always told to man up and deal with it on my own. I want to create safe spaces where guys can talk about their feelings without being judged or seen as weak. I'm currently working in finance, but I spend my evenings researching nonprofit management, mental health resources, and grant writing. I volunteer at crisis hotlines on weekends and I've started an anonymous blog where men can share their mental health stories. I know there's a huge need for this because suicide rates among men are so high, but there's still this toxic masculinity that prevents guys from getting help. My plan is to save enough money to take the leap into nonprofit work, even though it means a significant pay cut. I want to partner with schools, workplaces, and community centers to normalize mental health conversations for men. I believe that if we can change the narrative around men's mental health, we can save lives and create healthier relationships and communities.	2025-09-12 11:23:21.460167+00	f	\N	\N	t	\N
73	647778438	Mera sabse bada sapna hai ki main India mein mental health awareness spread karun, especially small towns aur rural areas mein jahaan abhi bhi ye topic taboo hai. Main psychology background se hun aur personally depression aur anxiety face kiya hai, toh main jaanti hun ki proper support system ki kitni zarurat hai. Main counseling practice start karna chahti hun jahaan affordable therapy provide kar sakun middle class families ko jo expensive private practice afford nahi kar sakte. Main social media pe mental health content create karti hun Hindi mein because English content relatable nahi hai sabke liye. Mujhe lagta hai ki India mein mental health ko Western concept samajhte hain, but actually hamari culture mein bhi depression, anxiety common hai. Main workshops conduct karna chahti hun schools, colleges, aur community centers mein. Parents ko educate karna chahti hun teenage mental health ke baare mein. Mera ultimate goal hai ki main ek mental health center open karun jahaan therapy, support groups, family counseling sab available ho reasonable rates mein. Main app develop karna chahti hun AI chatbot ke saath jo Hindi mein mental health support de sake. Family initially hesitant thi but ab support kar rahe hain.	2025-09-12 11:23:21.460167+00	f	\N	\N	t	\N
74	1437934486	I want to become a documentary filmmaker focused on telling stories of women who are breaking barriers in traditionally male-dominated fields around the world. I'm currently working in marketing, but I've been teaching myself video production, interviewing techniques, and film editing in my spare time. I've already started creating short documentary profiles of local women entrepreneurs, mechanics, engineers, and other trailblazers, and I post them on social media to build my portfolio. My ultimate goal is to travel to different countries and document how women are challenging gender norms and creating opportunities for themselves and others. I want to show that feminism looks different in every culture and that women's empowerment isn't a one-size-fits-all concept. I'm applying for grants, film school programs, and fellowship opportunities while saving money for equipment and travel expenses. I know the documentary film industry is competitive and often doesn't pay well, but I'm passionate about amplifying women's voices and creating content that inspires other women to pursue their dreams regardless of societal expectations.	2025-09-12 11:23:21.460167+00	f	\N	\N	t	\N
75	8482725798	Yaar mera life goal hai ki main India ke rural areas mein quality education provide karun, especially technology aur digital literacy ke field mein. Main software engineer hun aur acchi salary hai, but mujhe fulfillment nahi mil raha corporate job mein. Main weekends pe village schools mein jaata hun aur bachon ko basic computer skills sikhata hun. Main realize kiya hai ki digital divide bahut bada hai India mein - urban kids ko sab kuch available hai but rural kids ke paas basic facilities nahi hain. Main educational NGO start karna chahta hun jo mobile computer labs provide kare remote villages mein. Main solar-powered devices design kar raha hun jo offline content provide kar saken. Mera plan hai ki main B.Ed complete karun aur officially teacher banu, but modern methods use karun traditional subjects ke saath technology integrate kar ke. Main YouTube channel bhi start kiya hai educational content ke liye Hindi mein. Family ko initially weird laga ki stable tech job chod kar teaching mein jaana chahta hun, but gradually support mil raha hai. Main scholarship programs start karna chahta hun talented rural students ke liye jo engineering ya other professional courses pursue kar saken.	2025-09-12 11:23:21.460167+00	f	\N	\N	t	\N
76	647778438	I want to revolutionize the way we think about sustainable living by creating affordable, practical solutions for everyday people. I'm an environmental science graduate working in corporate consulting, but my real passion is developing accessible green technology for middle-class families. I spend my weekends building prototypes for things like affordable solar panel systems, water conservation devices, and urban farming solutions that don't require a huge initial investment. I believe environmental sustainability shouldn't be a luxury for wealthy people - it should be achievable for everyone. My goal is to start a company that manufactures and distributes eco-friendly products at cost-effective prices while also educating communities about environmental impact. I want to partner with local governments and community organizations to implement sustainable practices on a larger scale. I'm currently working on a business plan for modular solar systems that renters can install without permanent modifications to their homes. I know it's a competitive field, but I think there's a huge market for practical environmental solutions that don't require people to completely change their lifestyles overnight.	2025-09-12 11:23:21.460167+00	f	\N	\N	t	\N
77	1437934486	I've been thinking a lot about how social media has completely rewired our brains and expectations about relationships, success, and happiness. We're constantly comparing our behind-the-scenes to everyone else's highlight reels, and it's making us miserable. I notice how I feel anxious when I don't get enough likes on a post, or how I judge my own life based on what I see other people doing online. We're creating these curated versions of ourselves that aren't really authentic, and then we wonder why real-life interactions feel awkward or disappointing. I think we've lost the ability to be present in moments because we're always thinking about how to document them for social media. Even our relationships have become performative - we post couple photos to prove how happy we are, or we judge our relationships based on how Instagram-worthy they appear. I've been experimenting with taking social media breaks, and I always feel more content and focused when I'm not constantly consuming other people's content. But then FOMO kicks in and I end up scrolling again. I wonder if future generations will look back at this era and think we were all insane for voluntarily addicting ourselves to these platforms.	2025-09-12 11:24:38.292297+00	f	\N	\N	t	\N
78	8482725798	Main ek cheez observe kar raha hun ki humari generation ke paas bahut saare options hain but decision lene mein hum paralyzed ho jaate hain. Career choice se lekar life partner tak, everything mein infinite possibilities hain but iske wajah se hum constantly doubt karte rehte hain ki kya hum right choice kar rahe hain. Pehle ke zamane mein limited options the toh log grateful the jo milta tha. But ab hum always wonder karte rehte hain ki kya grass greener hai other side pe. Dating mein ye clearly dikhta hai - apps mein thousands of profiles hain but commitment karne mein darr lagta hai ki kahi koi better option miss na ho jaaye. Job mein bhi same hai - constantly lagta hai ki maybe other company mein better package milta, better work culture hota. Social media ne ye problem aur badha diya hai because hum constantly dekh rahe hain ki dusre log kya kar rahe hain aur compare kar rahe hain. Main sometimes sochta hun ki maybe less choice aur more gratitude ka combination better hota happiness ke liye. But fir main bhi choice paralysis ka victim hun same way.	2025-09-12 11:24:38.292297+00	f	\N	\N	t	\N
79	647778438	I've been observing how our generation is caught between traditional expectations and modern realities, and it's creating this weird identity crisis for a lot of us. Our parents' generation had clearer paths - you went to school, got a job, got married, bought a house, had kids, retired. But now everything is more complex and uncertain. Career paths are less linear, relationships happen later or not at all, homeownership is financially out of reach for many, and traditional milestones don't apply anymore. We're told to follow our passions but also to be financially responsible, to be independent but also to prioritize relationships, to live in the moment but also to plan for the future. The constant choice paralysis is exhausting. Dating apps give us infinite options but make it harder to commit to anyone. Remote work gives us flexibility but blurs the lines between personal and professional life. Social media connects us globally but makes us feel more isolated locally. I think we're the first generation to have this much information and this many choices, and we're not equipped to handle it. Sometimes I wonder if having fewer options actually made people happier because they spent less time questioning their decisions.	2025-09-12 11:24:38.292297+00	f	\N	\N	t	\N
80	1437934486	Main ek ajeeb sa observation share karna chahti hun ki technology ne humein zyada connected banane ka promise kiya tha but actually hum zyada isolated ho gaye hain. WhatsApp, Instagram, Facebook se hum constantly in touch hain logon se but meaningful conversations kam ho gayi hain. Hum videos dekhte hain, memes share karte hain, but real personal problems ya feelings discuss nahi karte. Dating apps ne options badha diye hain but genuine connections banane mein difficulty ho rahi hai because everyone replaceable lag raha hai. Online shopping convenient hai but instant gratification ka culture ban gaya hai. Work from home flexibility diya hai but work-life balance aur blur ho gaya hai. Main notice karti hun ki attention span kam ho gayi hai, patience kam ho gayi hai, boredom tolerate karna mushkil ho gaya hai. Pehle log actually baith kar baat karte the, books padhte the, nature enjoy karte the without documenting everything. Now everything content ban gaya hai social media ke liye. Sometimes main miss karti hun simpler times jab notifications nahi the, constant comparison nahi thi, aur present moment mein reh sakte the without FOMO.	2025-09-12 11:24:38.292297+00	f	\N	\N	t	\N
81	8482725798	I've been thinking about how technology promised to make our lives easier, but in many ways it's made everything more complicated and stressful. We have devices that can do anything, but we're more overwhelmed than ever. We can communicate with anyone instantly, but meaningful conversations seem harder to have. We have access to all human knowledge, but we're more confused and polarized than previous generations. Online shopping is convenient, but it's created this culture of instant gratification where we buy things we don't need. Dating apps give us access to thousands of potential partners, but relationships seem more superficial and disposable. Work emails follow us home, social media makes us feel inadequate, and news cycles keep us in a constant state of anxiety. I notice how my attention span has decreased, how I feel restless when I'm not stimulated by screens, and how I've lost the ability to be bored without immediately reaching for my phone. Part of me romanticizes simpler times when people had to actually talk to each other, read physical books, and be present in their own lives. But then I also appreciate how technology has given us opportunities, connections, and conveniences that would have been impossible before.	2025-09-12 11:24:38.292297+00	f	\N	\N	t	\N
\.


--
-- Data for Name: crush_leaderboard; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.crush_leaderboard (user_id, crush_count, week_start, last_updated) FROM stdin;
1437934486	2	2025-09-15	2025-09-15 09:49:40.63337+00
647778438	1	2025-09-15	2025-09-15 09:50:20.811609+00
8482725798	1	2025-09-15	2025-09-15 09:59:04.993094+00
\.


--
-- Data for Name: daily_dare_selection; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.daily_dare_selection (dare_date, dare_text, dare_source, source_id, created_at, submitter_id, category, difficulty, creator_notified) FROM stdin;
2025-09-07	Sing a song and upload it on a story	community	4	2025-09-07 17:30:08.809526+00	\N	general	medium	f
2025-09-08	Sing a song and upload it on a story	community	4	2025-09-08 02:05:02.099583+00	\N	general	medium	f
2025-09-09	Sing a song and upload it on a story	community	4	2025-09-09 17:30:08.745625+00	\N	general	medium	f
2025-09-10	Sing a song and upload it on a story	community	4	2025-09-10 17:30:08.859751+00	\N	general	medium	f
2025-09-12	Share a 'guilty pleasure' food + emoji combo 🍫😈	system	\N	2025-09-12 17:30:08.665655+00	\N	general	medium	f
2025-09-16	Fruit Race — 5–8s video: 2 fruits/veg ko “race” karvao (stop-motion ya push)\n\nUsko apne feed pe upload karo\n\nUse #darecomplete	community	8	2025-09-16 17:51:13.651455+00	\N	general	medium	f
2025-09-19	Fruit Race — 5–8s video: 2 fruits/veg ko “race” karvao (stop-motion ya push)\n\nUsko apne feed pe upload karo\n\nUse #darecomplete	community	8	2025-09-19 17:30:08.855018+00	\N	general	medium	f
\.


--
-- Data for Name: dare_feedback; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.dare_feedback (id, submission_id, event_type, user_id, dare_date, notified, created_at) FROM stdin;
\.


--
-- Data for Name: dare_responses; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.dare_responses (id, user_id, dare_date, response, response_time, completion_claimed, difficulty_selected, dare_text) FROM stdin;
\.


--
-- Data for Name: dare_stats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.dare_stats (user_id, current_streak, longest_streak, total_accepted, total_declined, total_expired, last_dare_date, badges, updated_at) FROM stdin;
\.


--
-- Data for Name: dare_submissions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.dare_submissions (id, submitter_id, dare_text, category, difficulty, approved, admin_approved_by, submission_date, created_at) FROM stdin;
6	647778438	Object Superhero — kisi household item ko paper/cape se “superhero” bana ke photo upload karo apne my post pe\n\nAnd neeche use tag \n\n #darecomplete	funny	easy	t	647778438	2025-09-15	2025-09-15 16:58:06.618948+00
7	647778438	Emoji Match — 1 emoji choose karo, waise shape me objects arrange karke photo upload karo apne feed pe \n\nUse #darecomplete	funny	easy	t	647778438	2025-09-15	2025-09-15 17:02:10.059093+00
8	647778438	Fruit Race — 5–8s video: 2 fruits/veg ko “race” karvao (stop-motion ya push)\n\nUsko apne feed pe upload karo\n\nUse #darecomplete	funny	easy	t	647778438	2025-09-15	2025-09-15 17:04:00.28768+00
\.


--
-- Data for Name: fantasy_board_reactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_board_reactions (id, user_id, fantasy_id, reaction_type, created_at) FROM stdin;
\.


--
-- Data for Name: fantasy_chat_sessions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_chat_sessions (id, a_id, b_id, started_at, ended_at, status) FROM stdin;
1	647778438	1437934486	2025-09-20 15:21:08.623693+00	2025-09-20 15:57:46.99666+00	ended
\.


--
-- Data for Name: fantasy_chats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_chats (id, match_id, chat_room_id, started_at, expires_at, boy_joined, girl_joined, message_count) FROM stdin;
\.


--
-- Data for Name: fantasy_match_notifs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_match_notifs (id, match_id, user_id, sent_at) FROM stdin;
61	39	8482725798	2025-09-19 14:40:54.795072
62	39	647778438	2025-09-19 15:10:01.818063
63	40	8482725798	2025-09-19 16:43:12.57638
64	40	647778438	2025-09-19 17:13:13.290287
65	41	8482725798	2025-09-19 18:48:01.814038
66	41	647778438	2025-09-19 19:18:02.54697
67	42	8482725798	2025-09-19 20:53:04.017866
68	42	647778438	2025-09-19 21:23:04.727241
69	43	8482725798	2025-09-19 22:58:03.874784
70	43	647778438	2025-09-19 23:28:04.755657
71	44	8482725798	2025-09-20 01:03:03.861324
72	44	647778438	2025-09-20 01:33:04.629648
73	45	8482725798	2025-09-20 03:08:09.101358
74	45	647778438	2025-09-20 03:43:07.363255
75	46	647778438	2025-09-20 05:45:45.731331
76	46	8482725798	2025-09-20 05:45:48.916767
77	47	647778438	2025-09-20 05:45:51.697263
78	47	1437934486	2025-09-20 05:45:54.487898
\.


--
-- Data for Name: fantasy_match_requests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_match_requests (id, requester_id, fantasy_id, fantasy_owner_id, status, created_at, responded_at, expires_at, cancelled_by_user_id, cancelled_at, cancel_reason, version) FROM stdin;
1	8482725798	18	647778438	approved	2025-09-19 10:13:27.69907+00	2025-09-19 10:14:52.284205+00	2025-09-20 04:57:01.792335+00	\N	\N	\N	1
2	8482725798	19	1437934486	declined	2025-09-19 10:34:37.606028+00	2025-09-19 10:34:49.686393+00	2025-09-20 04:57:01.792335+00	\N	\N	\N	1
4	647778438	22	1437934486	accepted	2025-09-20 03:58:33.846421+00	\N	2025-09-20 04:58:33.728767+00	\N	\N	\N	1
5	647778438	24	1437934486	accepted	2025-09-20 04:19:15.50317+00	\N	2025-09-20 05:19:15.385639+00	\N	\N	\N	1
6	1437934486	20	8482725798	accepted	2025-09-20 04:29:49.165426+00	\N	2025-09-20 05:29:49.046073+00	\N	\N	\N	1
7	1437934486	21	8482725798	rejected	2025-09-20 04:45:40.100663+00	\N	2025-09-20 05:45:39.983337+00	\N	\N	\N	1
8	1437934486	21	8482725798	cancelled	2025-09-20 04:58:10.353379+00	\N	2025-09-20 05:58:10.23578+00	\N	\N	\N	1
3	8482725798	18	647778438	cancelled	2025-09-19 10:35:11.834782+00	\N	2025-09-20 04:57:01.792335+00	\N	\N	\N	1
9	1437934486	20	8482725798	rejected	2025-09-20 05:51:40.554591+00	\N	2025-09-20 06:51:40.437565+00	\N	\N	\N	1
10	1437934486	25	647778438	accepted	2025-09-20 05:56:05.518767+00	\N	2025-09-20 06:56:05.400743+00	\N	\N	\N	1
11	1437934486	25	647778438	rejected	2025-09-20 06:10:45.30644+00	\N	2025-09-20 07:10:45.183789+00	\N	\N	\N	1
12	1437934486	25	647778438	cancelled	2025-09-20 06:16:43.245774+00	\N	2025-09-20 07:16:43.128954+00	\N	\N	\N	1
13	1437934486	25	647778438	cancelled	2025-09-20 06:29:38.516136+00	\N	2025-09-20 07:29:38.398381+00	\N	\N	\N	1
14	1437934486	25	647778438	cancelled	2025-09-20 07:13:30.537306+00	\N	2025-09-20 08:13:30.419529+00	\N	\N	\N	1
15	647778438	22	1437934486	accepted	2025-09-20 07:15:01.961833+00	\N	2025-09-20 08:15:01.844091+00	\N	\N	\N	1
16	647778438	24	1437934486	accepted	2025-09-20 07:39:26.183605+00	\N	2025-09-20 08:39:26.065613+00	\N	\N	\N	1
17	1437934486	25	647778438	accepted	2025-09-20 07:55:11.861792+00	\N	2025-09-20 08:55:11.744154+00	\N	\N	\N	1
18	647778438	24	1437934486	accepted	2025-09-20 08:15:15.117328+00	\N	2025-09-20 09:15:14.999355+00	\N	\N	\N	1
19	647778438	24	1437934486	accepted	2025-09-20 08:19:24.602941+00	\N	2025-09-20 09:19:24.484861+00	\N	\N	\N	1
20	647778438	27	1437934486	accepted	2025-09-20 14:59:33.54989+00	\N	2025-09-20 15:59:33.432255+00	\N	\N	\N	1
21	647778438	27	1437934486	accepted	2025-09-20 15:10:05.440421+00	\N	2025-09-20 16:10:05.322288+00	\N	\N	\N	1
22	647778438	27	1437934486	accepted	2025-09-20 15:20:40.040521+00	\N	2025-09-20 16:20:39.917704+00	\N	\N	\N	1
23	647778438	21	8482725798	rejected	2025-09-20 15:35:15.563024+00	\N	2025-09-20 16:35:15.443553+00	\N	\N	\N	1
24	647778438	21	8482725798	rejected	2025-09-20 15:43:21.190201+00	\N	2025-09-20 16:43:21.069786+00	\N	\N	\N	1
25	647778438	21	8482725798	rejected	2025-09-20 15:53:39.764245+00	\N	2025-09-20 16:53:39.644037+00	\N	\N	\N	1
26	647778438	21	8482725798	rejected	2025-09-20 16:20:10.61909+00	\N	2025-09-20 17:20:10.502366+00	\N	\N	\N	1
27	647778438	27	1437934486	pending	2025-09-20 16:33:30.558424+00	\N	2025-09-20 17:33:30.439069+00	\N	\N	\N	1
\.


--
-- Data for Name: fantasy_matches; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_matches (id, boy_id, girl_id, fantasy_key, created_at, expires_at, boy_ready, girl_ready, boy_is_premium, connected_at, status, chat_id, vibe, shared_keywords) FROM stdin;
43	8482725798	647778438	romantic:have-sex	2025-09-19 21:23:10.59223	2025-09-19 23:23:10.468418	f	f	f	\N	expired	\N	romantic	{sex,have}
44	8482725798	647778438	romantic:have-sex	2025-09-19 23:28:10.558403	2025-09-20 01:28:10.440349	f	f	f	\N	expired	\N	romantic	{sex,have}
45	8482725798	647778438	romantic:have-sex	2025-09-20 01:33:10.506283	2025-09-20 03:33:10.383184	f	f	f	\N	expired	\N	romantic	{sex,have}
39	8482725798	647778438	romantic:sex	2025-09-19 13:06:49.020051	2025-09-19 15:06:48.902666	f	f	f	\N	expired	\N	romantic	{sex}
40	8482725798	647778438	romantic:have-sex	2025-09-19 15:10:07.703115	2025-09-19 17:10:07.577902	f	f	f	\N	expired	\N	romantic	{sex,have}
41	8482725798	647778438	romantic:have-sex	2025-09-19 17:13:19.196142	2025-09-19 19:13:19.077652	f	f	f	\N	expired	\N	romantic	{have,sex}
42	8482725798	647778438	romantic:have-sex	2025-09-19 19:18:08.561601	2025-09-19 21:18:08.443662	f	f	f	\N	expired	\N	romantic	{sex,have}
46	8482725798	647778438	romantic:have-sex	2025-09-20 03:43:13.162138	2025-09-20 05:43:13.043073	f	f	f	\N	expired	\N	romantic	{sex,have}
47	1437934486	647778438	romantic:sex	2025-09-20 03:43:16.0198	2025-09-20 05:43:15.901127	f	f	f	\N	expired	\N	romantic	{sex}
\.


--
-- Data for Name: fantasy_stats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_stats (fantasy_id, views_count, reactions_count, matches_count, success_rate, last_updated) FROM stdin;
\.


--
-- Data for Name: fantasy_submissions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.fantasy_submissions (id, user_id, gender, fantasy_text, created_at, is_active, fantasy_key, submitted_count, vibe, keywords, active) FROM stdin;
6	1437934486	female	Have sex on a open beach	2025-09-10 07:50:17.258301	t	\N	1	romantic	{have,sex,open}	f
5	647778438	f	Wanna have sex on a beach	2025-09-10 07:49:26.501707	t	\N	1	romantic	{wanna,have,sex}	f
10	1437934486	f	Have sex with a teacher	2025-09-10 12:04:44.240362	t	\N	1	roleplay	{have,sex,teacher}	f
12	1437934486	f	Have sex with a teacher	2025-09-10 12:45:13.923492	t	\N	1	roleplay	{have,sex,teacher}	f
14	1437934486	f	To have threesome	2025-09-10 14:13:13.828411	t	\N	1	wild	{have,threesome}	f
15	647778438	f	To have threesome	2025-09-10 14:13:34.435804	t	\N	1	wild	{have,threesome}	f
17	647778438	f	Sex on a rain	2025-09-12 05:50:12.34533	t	\N	1	romantic	{sex,rain}	f
20	8482725798	m	Sex on a beach	2025-09-19 13:00:53.091147	t	\N	1	romantic	{sex,beach}	t
21	8482725798	m	Have sex on a running train	2025-09-19 13:50:24.122272	t	\N	1	romantic	{have,sex,running}	t
23	647778438	f	Sex on a mountain	2025-09-19 16:02:03.532031	t	\N	1	romantic	{sex,mountain}	f
18	647778438	f	Have sex on a rain	2025-09-19 10:04:50.956281	t	\N	1	romantic	{have,sex,rain}	f
25	647778438	f	Sex on a mountain	2025-09-20 05:54:58.218371	t	\N	1	romantic	{sex,mountain}	f
26	647778438	f	Have sex with four people	2025-09-20 14:24:00.898136	t	\N	1	romantic	{have,sex,four}	t
24	1437934486	m	Wanna have sex on a rooftop	2025-09-20 03:04:46.300267	t	\N	1	romantic	{wanna,have,sex}	f
22	1437934486	m	Have sex on a flight	2025-09-19 13:50:45.135218	t	\N	1	travel	{have,sex,flight}	f
19	1437934486	m	To have threesome	2025-09-19 10:12:35.958792	t	\N	1	wild	{have,threesome}	f
27	1437934486	m	Sex on a school	2025-09-20 14:44:11.558889	t	\N	1	romantic	{sex,school}	t
\.


--
-- Data for Name: feed_comments; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.feed_comments (id, post_id, author_id, author_name, text, created_at) FROM stdin;
9	5	647778438	champ7513	So now	2025-09-12 05:26:39.285389+00
12	8	1437934486	Rajendra	Ni e	2025-09-15 11:39:37.382905+00
13	8	1437934486	Rajendra	Bahot jyada	2025-09-15 11:41:04.179459+00
\.


--
-- Data for Name: feed_likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.feed_likes (post_id, user_id, created_at) FROM stdin;
5	1	2025-09-15 08:53:30.770041+00
8	2	2025-09-15 11:23:15.264278+00
\.


--
-- Data for Name: feed_posts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.feed_posts (id, author_id, created_at, content_type, file_id, text, reaction_count, comment_count, profile_id) FROM stdin;
36	1	2025-09-29 09:11:20.788727+00	photo	BQACAgUAAyEGAAS7uGd-AAM9aNpNOwe5B9ZZR-eQQvz0dcPeNcEAAswYAAI-KdlWYp4WJH52gM82BA		1	0	1
16	1	2025-09-28 14:48:03.570658+00	photo	BQACAgUAAyEGAAS7uGd-AAMpaNlKp2yzGKn-4PtnbDYYtMmyAQ4AAqMYAAJ6BdBW8BLVWTXlGnE2BA	Hmmm	1	1	\N
18	1	2025-09-28 16:47:37.164586+00	photo	BQACAgUAAyEGAAS7uGd-AAMraNlmrK9-IDDIXvDORCX4UDsvgJkAAtkYAAJ6BdBWyFbiq8o_8002BA	Ganesh bhai	0	0	\N
39	2	2025-09-29 09:38:42.247113+00	photo	BQACAgUAAyEGAAS7uGd-AANAaNpTpfTpxW0ciPqaJluR-x9bp5wAAvMYAAI-KdlWti3pyJYsTAY2BA		1	6	3
37	1	2025-09-29 09:12:23.806732+00	photo	BQACAgUAAyEGAAS7uGd-AAM-aNpNe2p1GiUOiNtANBAPdizngN8AAs0YAAI-KdlW8myXXBZG65Q2BA	Okllllll	1	4	\N
17	2	2025-09-28 14:58:40.245572+00	photo	BQACAgUAAyEGAAS7uGd-AAMqaNlNI7okktAJBt0sVy-DTwoUviwAAqYYAAJ6BdBWhm5fyutFRPs2BA		1	8	\N
21	1	2025-09-29 05:42:24.928437+00	photo	BQACAgUAAyEGAAS7uGd-AAMuaNocRAf7PD_sVqyVckahIH9zeNkAAjsYAAI-KdlWJC7TKhs_uMk2BA	Httpooo	0	0	\N
22	1	2025-09-29 05:58:21.618596+00	photo	BQACAgUAAyEGAAS7uGd-AAMvaNogAAGJ60M5lZACpH2CFysvwJbQAAJPGAACPinZVpPYkf55ho1CNgQ	Failed	0	0	1
23	1	2025-09-29 06:23:32.457558+00	photo	BQACAgUAAyEGAAS7uGd-AAMwaNol591JKyDuhMGtB7I7L9U4gh0AAl0YAAI-KdlWAAHQTr1jXzIaNgQ		0	0	\N
24	1	2025-09-29 06:34:50.637508+00	photo	BQACAgUAAyEGAAS7uGd-AAMxaNoojQAByKA1GkfCfkVJyellLxzrAAJjGAACPinZVgQDOSrEuEgLNgQ	Love	0	0	\N
25	1	2025-09-29 06:41:51.738881+00	photo	BQACAgUAAyEGAAS7uGd-AAMyaNoqM7CUax7Vux3IUK7OdancJ4gAAmoYAAI-KdlWWBKmXoxbZrw2BA	Nayshsjjsakow	0	0	\N
26	1	2025-09-29 06:42:03.434+00	photo	BQACAgUAAyEGAAS7uGd-AAMzaNoqPuIksrR0WuWYp8lqB8gV73cAAmsYAAI-KdlWGlnbe5zvh3g2BA	Nayshsjjsakow	0	0	\N
27	1	2025-09-29 06:43:39.836541+00	photo	BQACAgUAAyEGAAS7uGd-AAM0aNoqnsyVKtWZxsZKIOVtERxgljkAAm0YAAI-KdlW7WbTSegJckc2BA		0	0	1
15	2	2025-09-28 12:39:14.785179+00	photo	BQACAgUAAyEGAAS7uGd-AAMoaNksdtwN1OAO3RQay5k_NWh9H10AAnoYAAJ6BdBWSQzOAS-g5c42BA		0	0	\N
28	1	2025-09-29 06:45:50.399147+00	photo	BQACAgUAAyEGAAS7uGd-AAM1aNorIb480Lw30sZF4XDZhgNN-XQAAnAYAAI-KdlW6XGRh_2VfuI2BA	Replay	0	0	\N
29	1	2025-09-29 07:02:43.213533+00	photo	BQACAgUAAyEGAAS7uGd-AAM2aNovFn1NK-nXxlwWkdCa4vAuFgkAAnUYAAI-KdlWwINn5JZRUDY2BA		0	0	1
30	1	2025-09-29 07:18:16.482284+00	photo	BQACAgUAAyEGAAS7uGd-AAM3aNoyu5wFd_nODQZhBwSFsvjwAQkAAoAYAAI-KdlWd6LL7ZxkOCA2BA	11111	0	0	1
31	1	2025-09-29 07:30:02.439301+00	photo	BQACAgUAAyEGAAS7uGd-AAM4aNo1fXNUsJCgynagr9HOP3KIIZcAAo0YAAI-KdlWwagFL5CTCsc2BA		0	0	1
32	1	2025-09-29 07:31:26.58719+00	photo	BQACAgUAAyEGAAS7uGd-AAM5aNo10f9lNMzS3ZubTlpARn1VXxsAAo4YAAI-KdlW2-F4cAsj3FU2BA		0	0	\N
33	1	2025-09-29 08:05:01.908692+00	photo	BQACAgUAAyEGAAS7uGd-AAM6aNo9sYPPnpsbjh9wBPldAAEOYb6uAAKpGAACPinZVgABIT6AgCoe0DYE		0	0	1
34	1	2025-09-29 08:10:53.332348+00	photo	BQACAgUAAyEGAAS7uGd-AAM7aNo_EFRm28DY6x0MMnSh9An5AbkAArAYAAI-KdlWVieIBXOXiS02BA		0	0	\N
35	1	2025-09-29 08:51:48.890958+00	photo	BQACAgUAAyEGAAS7uGd-AAM8aNpIpzfY0szr3MxnjWd0a5vhjb4AArwYAAI-KdlWZoGKJsQqYq42BA		0	0	1
38	2	2025-09-29 09:36:27.686694+00	photo	BQACAgUAAyEGAAS7uGd-AAM_aNpTH3ahqLa23K4tYVcaoaMmFrcAAvEYAAI-KdlWq09D7e9ol2A2BA		0	0	\N
\.


--
-- Data for Name: feed_profiles; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.feed_profiles (uid, username, bio, is_public, photo) FROM stdin;
647778438	Bunny	Radheshyam	t	\N
\.


--
-- Data for Name: feed_reactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.feed_reactions (post_id, user_id, emoji, created_at) FROM stdin;
\.


--
-- Data for Name: feed_views; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.feed_views (post_id, viewer_id, viewed_at) FROM stdin;
2	1437934486	2025-09-01 17:12:39.354745+00
3	1437934486	2025-09-01 17:12:54.585657+00
2	647778438	2025-09-01 17:13:08.410439+00
3	647778438	2025-09-01 17:13:18.363777+00
1	1437934486	2025-09-01 17:19:43.10122+00
3	8482725798	2025-09-02 06:58:59.232038+00
2	8482725798	2025-09-02 07:07:18.576208+00
4	8482725798	2025-09-02 10:22:50.398078+00
1	647778438	2025-09-02 20:29:58.893989+00
5	647778438	2025-09-03 06:33:22.441776+00
5	8482725798	2025-09-05 12:03:47.967117+00
1	8482725798	2025-09-05 12:07:18.613902+00
6	1437934486	2025-09-12 05:25:50.687132+00
6	647778438	2025-09-12 07:04:55.057747+00
6	8482725798	2025-09-14 03:47:11.348731+00
5	1437934486	2025-09-14 03:56:13.906943+00
5	1040560837	2025-09-14 06:10:57.250055+00
7	1437934486	2025-09-14 06:11:27.209978+00
7	647778438	2025-09-14 06:12:13.825344+00
8	1437934486	2025-09-15 09:58:33.73302+00
8	647778438	2025-09-15 10:07:56.369905+00
7	8482725798	2025-09-15 11:40:35.92324+00
9	647778438	2025-09-15 13:18:41.95538+00
\.


--
-- Data for Name: friend_chats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.friend_chats (id, a, b, opened_at, closed_at) FROM stdin;
\.


--
-- Data for Name: friend_msg_requests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.friend_msg_requests (id, sender, receiver, text, created_at, status) FROM stdin;
\.


--
-- Data for Name: friend_requests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.friend_requests (requester_id, target_id, created_at) FROM stdin;
\.


--
-- Data for Name: friends; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.friends (user_id, friend_id, added_at) FROM stdin;
\.


--
-- Data for Name: friendship_levels; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.friendship_levels (user1_id, user2_id, interaction_count, level, last_interaction, created_at) FROM stdin;
647778438	1437934486	3	1	2025-09-14 05:22:13.803703+00	2025-09-14 04:43:48.062432+00
\.


--
-- Data for Name: game_questions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.game_questions (game, question, added_by, added_at) FROM stdin;
truth	what's your dirtiest secret?	647778438	2025-08-29 18:33:24.047301+00
\.


--
-- Data for Name: idempotency_keys; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.idempotency_keys (key, operation, result, created_at) FROM stdin;
\.


--
-- Data for Name: likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.likes (id, post_id, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: maintenance_log; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.maintenance_log (id, operation, status, details, duration_seconds, executed_at) FROM stdin;
\.


--
-- Data for Name: miniapp_comments; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_comments (id, post_id, author_id, text, parent_id, created_at) FROM stdin;
\.


--
-- Data for Name: miniapp_follows; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_follows (follower_id, followee_id, created_at, status) FROM stdin;
\.


--
-- Data for Name: miniapp_likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_likes (post_id, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: miniapp_post_views; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_post_views (post_id, user_id, viewed_at) FROM stdin;
\.


--
-- Data for Name: miniapp_posts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_posts (id, author_id, type, caption, media_url, media_type, visibility, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: miniapp_profiles; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_profiles (user_id, username, display_name, bio, avatar_url, is_private, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: miniapp_saves; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.miniapp_saves (post_id, user_id, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: moderation_events; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.moderation_events (id, tg_user_id, kind, token, sample, created_at) FROM stdin;
1	\N	slur	chutiya	you are a chutiya	2025-09-03 17:48:21.050077+00
2	\N	slur	mc	MC BC	2025-09-03 17:48:22.0991+00
3	\N	slur	madarchod	madarchod sale	2025-09-03 17:48:23.054247+00
4	\N	slur	retard	fucking retard	2025-09-03 17:48:24.008633+00
5	\N	soft_warn	onlyfans	check my onlyfans	2025-09-03 17:48:24.964057+00
6	\N	slur	chutiya	you are a chutiya	2025-09-03 17:48:25.919194+00
7	\N	slur	mc	MC BC	2025-09-03 17:48:26.872991+00
8	\N	slur	madarchod	madarchod sale	2025-09-03 17:48:27.825869+00
9	\N	slur	retard	fucking retard	2025-09-03 17:48:28.778935+00
10	\N	slur	kys	kys loser	2025-09-03 17:48:29.73383+00
11	\N	soft_warn	onlyfans	check my onlyfans	2025-09-03 17:48:30.6872+00
12	\N	soft_warn	porn	porn porn porn	2025-09-03 17:48:31.697992+00
13	12345	slur	chutiya	you are a chutiya	2025-09-03 17:50:19.263461+00
14	12345	slur	madarchod	madarchod BC	2025-09-03 17:50:20.228409+00
15	12345	slur	fuck you	I wanna fuck you	2025-09-03 17:50:21.177348+00
16	12345	soft_warn	onlyfans	check my onlyfans link	2025-09-03 17:50:22.129052+00
17	\N	slur	chutiya	you are a chutiya	2025-09-03 18:05:24.368308+00
18	\N	slur	bc	MC BC	2025-09-03 18:05:25.357315+00
19	\N	slur	madarchod	madarchod sale	2025-09-03 18:05:26.317173+00
20	\N	slur	retard	fucking retard	2025-09-03 18:05:27.275054+00
21	\N	slur	kys	kys loser	2025-09-03 18:05:28.236169+00
22	\N	soft_warn	onlyfans	check my onlyfans	2025-09-03 18:05:29.223618+00
23	\N	soft_warn	porn	porn porn porn	2025-09-03 18:05:30.193615+00
24	\N	soft_warn	escort	escort services	2025-09-03 18:05:31.151198+00
25	12345	slur	chutiya	you are a chutiya	2025-09-03 18:21:51.170041+00
\.


--
-- Data for Name: muc_char_options; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_char_options (id, question_id, opt_key, text) FROM stdin;
1	1	keep_sarah	Keep it Sarah - it suits her
2	1	emily	Emily Richardson
3	1	maya	Maya Chen
4	1	community_choice	Let the community suggest names
5	2	softer	Show his vulnerable side more
6	2	mysterious	Keep him dark and mysterious
7	2	protective	Focus on his protective instincts
8	2	conflicted	Explore his duty vs. love conflict
9	3	confidence	Gain confidence in high-stakes situations
10	3	leadership	Step up as a leader
11	3	complexity	Reveal hidden depths and complexity
12	3	sacrifice	Show willingness to sacrifice for love
13	4	triangle	Keep the love triangle tension
14	4	alex_endgame	Alex is clearly the endgame
15	4	ryan_endgame	Ryan is clearly the endgame
16	4	poly_option	Explore polyamorous possibilities
\.


--
-- Data for Name: muc_char_questions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_char_questions (id, series_id, prompt, question_key, active_from_episode_id) FROM stdin;
1	2	What should Sarah's name really be?	sarah_real_name	\N
2	2	How should Alex's character develop?	alex_development	\N
3	2	What should Ryan's biggest character growth be?	ryan_growth	\N
4	2	Should there be a love triangle or clear choice?	romance_direction	\N
\.


--
-- Data for Name: muc_char_votes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_char_votes (id, question_id, option_id, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: muc_characters; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_characters (id, series_id, name, role, bio_md, attributes, secrets) FROM stdin;
1	2	Sarah	protagonist	Mysterious transfer student who arrives at Midnight University under secretive circumstances. The community will shape her story.	{"popularity": 3, "trust_level": 5, "mystery_level": 9}	{"deeper": "family_scandal", "deepest": "witness_protection", "surface": "transfer_reason_unknown"}
2	2	Alex	mysterious_love_interest	Enigmatic senior student who seems to know more than he reveals. Dark eyes that hold secrets.	{"charm_level": 8, "danger_level": 7, "mystery_level": 10}	{"deeper": "family_connections", "deepest": "true_identity", "surface": "late_night_activities"}
3	2	Ryan	helpful_friend	Friendly, approachable student who immediately offers to help Sarah. But are his motives pure?	{"hidden_agenda": 4, "kindness_level": 9, "trustworthy_level": 7}	{"deeper": "family_rivalry", "deepest": "protective_mission", "surface": "crush_on_sarah"}
4	2	Professor Chen	suspicious_authority	Psychology professor who takes unusual interest in Sarah. Asks probing questions during class.	{"authority_level": 9, "knowledge_level": 10, "suspicion_level": 8}	{"deeper": "past_connection", "deepest": "guardian_role", "surface": "research_interest"}
\.


--
-- Data for Name: muc_episodes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_episodes (id, series_id, idx, title, teaser_md, body_md, cliff_md, publish_at, close_at, status) FROM stdin;
2	2	2	The Warning Note	📝 The note contains a warning... but from whom?	**Episode 2: The Warning Note**\n\nSarah's hands shake as she unfolds the piece of paper. The handwriting is elegant but urgent:\n\n*"Don't trust anyone here. Meet me at the library at midnight tomorrow. Come alone. Your life may depend on it. -A friend"*\n\nHer heart pounds. She's been here less than an hour and someone is already warning her? About what? About whom?\n\nThe next day, classes blur together. Every face seems suspicious. Professor Chen watches her intently during Psychology class, asking pointed questions about "fresh starts" and "running from the past."\n\nDuring lunch, two students approach her table.\n\n"You're the new girl, right?" The first one has kind eyes and an easy smile. "I'm Ryan. Welcome to Midnight University. It can be overwhelming at first."\n\nThe second remains silent, his dark eyes studying her with unsettling intensity. "Alex," he finally introduces himself. "Word travels fast here about new arrivals."\n\n"Especially mysterious midnight arrivals," Ryan adds with a laugh. "Need someone to show you around?"\n\nSarah feels torn. Ryan seems genuine, helpful. But Alex... there's something magnetic about his quiet mystery. Something dangerous.\n\nAs evening approaches, the warning note burns in her pocket. *Meet me at the library at midnight.*\n\nBut which of these new acquaintances can she trust? And who wrote that note?\n\n*The clock is ticking toward midnight. A choice must be made.*	🏃‍♂️ As Sarah approaches the library at 11:55 PM, she sees two figures in the shadows - both Ryan and Alex are there. But which one sent the note?	2025-09-23 14:30:00+00	\N	published
3	2	3	Midnight Confrontation	🌙 Two boys, one choice, and a secret that changes everything...	**Episode 3: Midnight Confrontation**\n\nThe library looms dark against the night sky. Sarah's footsteps echo on the stone pathway as she approaches the entrance. Her heart stops - both Ryan and Alex are there, standing in the shadows on opposite sides of the building.\n\nRyan notices her first, his face lighting up with relief. "Sarah! Thank God you're safe. I was worried when I didn't see you at dinner."\n\nAlex steps forward from the darkness, his expression unreadable. "You came. Good."\n\n"Wait..." Sarah looks between them, confusion and fear mixing in her chest. "Which one of you sent the note?"\n\nBoth boys look genuinely surprised.\n\n"What note?" Ryan asks, concern creeping into his voice.\n\nAlex's eyes narrow. "Someone contacted you? Sarah, this is more serious than I thought."\n\n"You thought what was serious?" Sarah demands, backing toward the library entrance.\n\nSuddenly, the library doors swing open from inside. "Come in, all of you," Professor Chen's voice calls out. "It's time you knew the truth."\n\nInside, the professor switches on a single lamp, casting long shadows across the books. His usual friendly demeanor is gone, replaced by something more intense.\n\n"Sarah, your father didn't just send you here for a 'fresh start.' You're here because you witnessed something. Something that powerful people want to keep buried."\n\nRyan gasps. "Witness protection? But why here?"\n\n"Because Midnight University isn't just any school," Alex says quietly, his voice carrying a weight Sarah hasn't heard before. "It's a sanctuary. For people who need to disappear."\n\nProfessor Chen nods. "Both boys have been assigned to watch over you, Sarah. But they don't know about each other's assignment. Or about the third party that's been tracking you."\n\n*A third party? Sarah's world is turning upside down. Who can she trust? And what exactly did she witness that was worth killing for?*	⚡ The lights suddenly cut out, plunging them into darkness. A new voice whispers from the shadows: "Too late. They found her."	2025-09-24 14:30:00+00	\N	published
4	2	4	Secrets in the Dark	🔦 In the darkness, truths emerge and alliances shift...	**Episode 4: Secrets in the Dark**\n\n"Nobody move," Alex's voice cuts through the darkness, suddenly commanding and authoritative. The sound of a door slamming echoes through the library.\n\n"Emergency lighting should kick in any second," Professor Chen whispers. "Sarah, stay close to me."\n\nBut Ryan's hand finds hers first in the darkness. "I've got you," he says softly, and something in his voice makes her trust him completely.\n\nRed emergency lights flicker on, bathing everything in an eerie glow. The mysterious voice has vanished, but the threat lingers in the air.\n\nAlex pulls out what looks like a sophisticated walkie-talkie. "Base, we have a Code Red at Location Seven. Request immediate backup." His casual student demeanor has completely disappeared.\n\n"Alex?" Sarah stares at him. "Who are you really?"\n\n"Federal protection services," he admits, not meeting her eyes. "I've been assigned to your case since the beginning."\n\nRyan laughs bitterly. "Federal? Try private security. Hired by her father's company to make sure she stays quiet."\n\n"You're both wrong," Professor Chen says quietly. "Alex works for the government. Ryan works for the corporation. And I... I work for your mother, Sarah."\n\nThe room falls silent except for the humming of the emergency lights.\n\n"My mother is dead," Sarah whispers.\n\n"That's what everyone was supposed to think," Chen replies. "Including you. But she's very much alive, and she's been orchestrating this entire situation to keep you safe."\n\nSarah's legs give out. Ryan catches her, his arms strong and steady. But she finds herself looking at Alex, searching his dark eyes for the truth.\n\n"So none of this is real?" she asks, her voice breaking. "The school, the students, even you two... it's all fake?"\n\n"The danger is real," Alex says firmly. "And so are our feelings for you."\n\nRyan nods, his grip on her tightening protectively. "Some things can't be faked, Sarah."\n\n*But with three different organizations involved and her mother apparently alive, who is the real enemy? And which boy is telling her the truth about his feelings?*	📱 Sarah's phone buzzes with a message from an unknown number: "Meet me at the clock tower in one hour. Come alone. It's time you met your mother. -M"	2025-09-25 14:30:00+00	\N	published
5	2	5	The Mother's Gambit	👤 A mother's love, a daughter's choice, and a dangerous reunion...	**Episode 5: The Mother's Gambit**\n\nThe clock tower stands against the star-filled sky like a monument to secrets. Sarah climbs the spiral staircase alone, despite both Alex and Ryan's protests. Some reunions, she decided, require solitude.\n\nAt the top, a woman in elegant clothes waits by the window, her back to the stairs. When she turns, Sarah sees her own eyes reflected in a face she thought she'd never see again.\n\n"Hello, my darling," her mother says, voice trembling with emotion.\n\n"You let me think you were dead for three years," Sarah whispers, anger and love warring in her chest.\n\n"To keep you safe. The people who killed your father wanted our entire family eliminated. Faking my death was the only way."\n\nSarah's mother moves closer, her hands reaching out tentatively. "I've watched you from afar. Seen you grow into this strong, beautiful young woman. But when you witnessed the Richardson murder, everything changed."\n\n"The Richardson murder..." Sarah's mind reels. "The man in the alley. I saw his face."\n\n"Marcus Richardson was about to expose a corruption ring that goes to the highest levels of government and corporate America. They silenced him, and you were the only witness."\n\n"So you sent me here."\n\n"I sent you to the one place I knew you'd be protected. Professor Chen is my oldest friend. Alex is the best agent the bureau has. And Ryan..." Her mother smiles softly. "Ryan volunteered for this assignment when he found out it was you."\n\n"Volunteered?"\n\n"He's the son of the police chief in your hometown. He's been in love with you since high school, Sarah. When the protection order came through, he pulled every string to be assigned to your case."\n\nSarah's heart pounds. "And Alex?"\n\n"Alex is duty-bound. Professional. But I've seen the way he looks at you in the surveillance footage. Both boys are genuinely protecting you now, not just following orders."\n\nHer mother steps closer, placing a gentle hand on Sarah's face. "The question is, darling, what do you want to do? We can relocate you again, give you a completely new identity. Or..."\n\n"Or?"\n\n"You can stay here. Help us build a case against the people who killed your father. It's dangerous, but with both boys and Professor Chen watching over you..."\n\nSarah looks out at the campus below, where two figures wait anxiously by the library - Alex and Ryan, both ready to risk everything for her.\n\n*A choice that will determine not just her future, but the futures of everyone she's grown to care about.*	💥 A sniper's laser dot suddenly appears on her mother's forehead. "They found us," her mother gasps, pushing Sarah to the floor.	2025-09-26 14:30:00+00	\N	published
6	2	6	Under Fire	🎯 When bullets fly, true loyalty is revealed...	**Episode 6: Under Fire**\n\nThe first shot shatters the clock tower window. Sarah's mother tackles her to the stone floor as glass rains down around them.\n\n"Stay down!" her mother shouts, pulling out a concealed pistol with practiced ease. "They've found us faster than we anticipated."\n\nBelow, chaos erupts on the campus. Sarah can see Alex and Ryan sprinting toward the tower, but armed figures are emerging from the tree line, cutting off their approach.\n\n"Mom, who are these people?"\n\n"Richardson's killers. They've been tracking us through every surveillance system, every digital footprint." Her mother fires three quick shots through the broken window. "I should have known they'd never stop hunting."\n\nSarah's phone buzzes with frantic texts:\n*Alex: "Stay down. Help is coming."*\n*Ryan: "Trust no one but Chen. Building surrounded."*\n\n"We need to get to the roof," her mother says. "Extraction helicopter is en route."\n\nThey crawl toward the narrow staircase leading upward, but footsteps echo from below - someone is climbing up.\n\n"Sarah?" Professor Chen's voice calls out. "Are you safe?"\n\nHer mother freezes, gun trained on the staircase. "Chen was supposed to be at the safe house."\n\n"Sarah, don't trust her!" Alex's voice suddenly shouts from below. "Check her left wrist!"\n\nSarah looks at her mother's wrist and sees it - a small tattoo. The same symbol she saw on the man who killed Richardson.\n\n"You're one of them," Sarah breathes, horror washing over her.\n\nHer mother's expression shifts from loving to cold. "I'm sorry, darling. But some secrets are worth more than family."\n\nThe gun turns toward Sarah just as Ryan bursts through the window on a rope, swinging in from the outside. He tackles Sarah's mother, the weapon spinning away across the stone floor.\n\nAlex appears at the top of the stairs, his own gun drawn. "It was a trap from the beginning. Your mother isn't in hiding - she's the one who ordered the hit on Richardson."\n\nSarah's world crumbles. "But why?"\n\n"Richardson discovered she was embezzling millions from the children's charity she ran. Your father found out too. That's why they both had to die."\n\nHer mother laughs from where Ryan holds her down. "And now you know too much as well, my dear daughter."\n\n*The woman who gave her life has been trying to take it away. But with bullets flying and trust shattered, who can Sarah believe anymore?*	🚁 A helicopter approaches, but is it rescue or reinforcement for her mother's allies? Sarah must make a split-second choice.	2025-09-27 14:30:00+00	\N	published
7	2	7	Truth and Consequences	⚖️ In the final hour, all secrets are revealed and hearts are chosen...	**Episode 7: Truth and Consequences**\n\nThe helicopter hovers above the clock tower, its searchlight illuminating the chaos below. Sarah sees the pilot - it's Professor Chen.\n\n"That's our ride!" Alex shouts over the rotor noise, helping Ryan restrain her mother.\n\n"How do we know he's not part of this too?" Sarah calls back, her trust in everyone shattered.\n\nHer mother laughs bitterly from the ground. "Oh, Chen's clean. Annoyingly, consistently clean. Always was, even in college."\n\nProfessor Chen's voice crackles through a megaphone from the helicopter: "Sarah, I've got federal agents and media crews en route. Your mother's organization is finished!"\n\nAs if summoned by his words, the sound of sirens fills the night air. Police cars, FBI vehicles, and news vans converge on the campus from all directions.\n\n"It's over," Alex tells Sarah's mother. "The Richardson case, the charity fraud, all of it. We have everything."\n\nSarah looks between Alex and Ryan - both disheveled, both bleeding from minor cuts, both looking at her with genuine concern. "And what about you two? Now that the mission is over..."\n\nRyan steps forward first, his hand gentle on her cheek. "I need you to know - I volunteered for this assignment because I've been in love with you since sophomore year of high school. The protection job just gave me a chance to finally tell you."\n\nAlex holsters his weapon, his dark eyes intense. "I was assigned to keep you safe. But somewhere along the way, it became personal. I've never broken protocol before, but for you..."\n\n"For me, what?" Sarah asks softly.\n\n"For you, I'd quit the bureau tomorrow if it meant we could have something real."\n\nHer mother snorts from the ground. "How touching. Romeo and Romeo, fighting over Juliet."\n\nBut Sarah isn't listening to her anymore. She looks at the two boys who risked everything to save her life, who stood by her when her own mother betrayed her.\n\nThe helicopter begins to descend, Chen preparing to land on the tower roof. Federal agents stream into the building below. Her old life is ending, but a new one is beginning.\n\n"I don't know what happens next," Sarah tells Alex and Ryan. "I don't know who I am anymore, or what I want."\n\n"You're Sarah," Ryan says simply. "You're brave and smart and worth protecting."\n\n"You're a survivor," Alex adds. "And whatever you choose, wherever you go, you don't have to face it alone."\n\nAs they help load her mother into the helicopter in custody, Sarah realizes something important: for the first time in years, she gets to choose her own path.\n\n*The mystery of the new girl is solved. But the mystery of her heart - and which boy she'll choose - is just beginning.*\n\n**End of Week 1**\n\n**Community Choice: What should Sarah do next?**\n- Stay at Midnight University with Ryan\n- Join Alex in federal service\n- Start fresh somewhere new, alone\n- Something else entirely...	💝 As the dust settles, both boys wait for Sarah's decision. But first, she has something important to say to both of them...	2025-09-28 14:30:00+00	\N	published
17	2	8	Episode	\N	1A: The Midnight Arrival" The last bus groaned to a halt at the gates of Midnight University. Its clock tower struck twelve, the chimes rolling across the quiet campus like a warning. Sarah stepped down, her backpack the only weight on her shoulders, and her heart beat with a nervous rhythm. She was the new transfer, arriving late in the semester and for reasons she'd rather not explain, she couldn't start like the others had. The campus looked alive, even at this strange hour. Dorm lights flickered, shadows moved in windows, laughter floated across the courtyard. It was as though no one here ever slept. A voice cut through the night. "You must be the transfer student." From the darkness emerged Professor Chen, his silver-rimmed glasses catching the moonlight. He was elegant in a way that unsettled her, his calm steps echoing too deliberately on the pavement. "Sarah," she answered, keeping her last name tucked away. "Indeed," Chen replied smoothly. "Unusual time to begin your studies. But then…" his smile was faint "…this is an unusual place." As he led her across the courtyard, Sarah realized she was about to meet the people who would change everything. Little did she know, five faces awaited her in the shadows of Midnight University. Each would leave their mark on her story. Each would become part of the mystery she was walking into. The question was... which one could she trust?	\N	2025-09-23 07:12:57.170397+00	\N	published
18	2	9	Episode	\N	1B: Five Faces" As Sarah followed Professor Chen deeper into the campus, she encountered five people who would shape her destiny at Midnight University. Aarav - The Golden Boy The first was a boy leaning against the noticeboard, framed by the glow of fairy lights strung for some forgotten event. His laughter carried across the night as he charmed a circle of students around him. When Sarah passed, he noticed instantly that smile, flawless and warm, already reaching his eyes. "New face," Aarav called out, casual yet deliberate. "Welcome to Midnight. You picked a dangerous time to arrive." Everyone laughed, though Sarah couldn't tell if he was joking. His confidence was magnetic, the kind of presence that drew people like moths. Still, something in that easy grin felt rehearsed, like a mask he wore perfectly. Rey - The Outsider In the far corner of the library window sat Rey, hunched over an open laptop. His sharp profile glowed in blue light. He didn't join the laughter, didn't even look up not until Sarah's reflection passed across the glass. For a moment, their eyes met through the pane. He didn't smile. Didn't wave. Just watched, as though memorizing her face before returning to his screen. The way his fingers tapped at the keys, urgent and precise, gave her the strange impression he was searching for something or someone. Maya - The Roommate When Professor Chen finally led her to the dorm, the door swung open and out spilled Maya, barefoot, holding a mug of instant coffee and wearing a grin that was half mischief, half welcome. "You must be Sarah! Finally, someone to balance out the crazy around here." Her voice was warm, teasing, already tugging Sarah into comfort. Maya filled the silence with chatter which classes were impossible, which professors were suspicious, which seniors were worth avoiding. She was quick to laugh, quicker to hide the flicker in her eyes whenever Sarah asked about the "weird things" she'd noticed. It was as though she wanted to protect Sarah, but also feared saying too much. Lena - The Rival They didn't meet Lena in the friendliest way. As Sarah navigated the corridor, she bumped into a tall girl balancing a stack of books. The pile crashed down. "Watch it," Lena snapped, her tone sharp but her eyes sharper. She picked up her books with practiced precision, shooting Sarah a look that mixed irritation with a subtle challenge. Her reputation preceded her top of her class, unshakable confidence, and a sharp tongue. "Transfer student, huh? Try not to get in my way." It wasn't a threat. It was a promise. Professor Chen - The Mentor (or Something More?) Back in her dorm room, Professor Chen placed the keys gently in Sarah's hand. "Sweet dreams, Miss Sarah. Tomorrow, classes begin. I do hope you'll find our Psychology program… enlightening." His words lingered, as though chosen too carefully. Finally alone, Sarah unpacked her single bag. The room was quiet, almost comforting until she noticed the envelope under her desk. It hadn't been there when she walked in. Her fingers trembled as she opened it. The handwriting was messy, hurried: "Not everything here is what it seems. Trust the wrong person, and it will be your last mistake." She looked again at the faces she had just met Aarav, Rey, Maya, Lena, Chen. Each had smiled, or frowned, or stared, but all had left her unsettled in their own way. Midnight University was beautiful. Midnight University was alive. But Midnight University was hiding something. And Sarah, whether she liked it or not, had just stepped into its web.	\N	2025-09-23 07:13:45.438753+00	\N	published
\.


--
-- Data for Name: muc_poll_options; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_poll_options (id, poll_id, opt_key, text, next_hint, idx) FROM stdin;
5	2	alone	🚶‍♀️ Yes, go alone as requested	Trust can be dangerous...	0
6	2	tell_ryan	🤝 Tell Ryan and ask for help	Sometimes kindness hides motives...	0
7	2	tell_alex	🌙 Tell Alex about the note	Mystery attracts mystery...	0
8	2	avoid	🏃‍♀️ Don't go at all	Running away isn't always cowardice...	0
9	3	alex	🌙 Alex - his mystery is magnetic	Danger and attraction often dance together...	0
10	3	ryan	☀️ Ryan - his kindness feels genuine	Sometimes the obvious choice is right...	0
11	3	chen	👨‍🏫 Professor Chen - authority figure	Teachers don't always have students' best interests...	0
12	3	nobody	🚫 Nobody - trust no one	Isolation is its own kind of prison...	0
13	4	mother	👤 Go meet her "mother" immediately	Family reunions aren't always joyful...	0
14	4	boys	💑 Bring both boys with her	Safety in numbers, but secrets in crowds...	0
15	4	escape	🏃‍♀️ Try to escape the campus entirely	Sometimes running is the only option...	0
16	4	investigate	🔍 Investigate her mother's claims first	Truth and lies often wear the same face...	0
17	5	alex_duty	🛡️ Alex - professional and capable	Duty-bound protection can become something more...	0
18	5	ryan_heart	💝 Ryan - genuine and devoted	Love-driven protection knows no bounds...	0
19	5	both	🤝 Both - she needs them equally	Two hearts can share one mission...	0
20	5	independence	👑 Neither - she protects herself	The strongest protection comes from within...	0
21	6	forgive	💔 Try to understand her mother's choices	Forgiveness doesn't mean forgetting...	0
22	6	justice	⚖️ Ensure she faces full justice	Justice and revenge walk a thin line...	0
23	6	protect_others	🛡️ Focus on protecting others from her	Sometimes love means letting go...	0
24	6	personal_closure	🔐 Seek personal closure first	Healing begins with understanding...	0
25	7	ryan_normal	🏠 Stay with Ryan and build a normal life	Normal life has its own adventures...	0
26	7	alex_service	🌙 Join Alex in federal service	Some people are meant for extraordinary paths...	0
27	7	fresh_start	🌅 Start completely fresh, alone	Independence can be the greatest strength...	0
28	7	poly_choice	💕 Find a way to keep both boys close	The heart doesn't always follow conventional rules...	0
43	13	opt_1	Mysterious and intriguing	\N	0
44	13	opt_2	Dangerous and threatening	\N	1
45	13	opt_3	Beautiful but unsettling	\N	2
46	13	opt_4	Exciting and full of secrets	\N	3
47	14	opt_1	Aarav (the golden boy)	\N	0
48	14	opt_2	Rey (the outsider)	\N	1
49	14	opt_3	Maya (the roommate)	\N	2
50	14	opt_4	Lena (the rival)	\N	3
51	14	opt_5	Professor Chen (the mentor)	\N	4
\.


--
-- Data for Name: muc_polls; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_polls (id, episode_id, prompt, layer, allow_multi) FROM stdin;
2	2	Should Sarah go to the library meeting alone?	deeper	f
3	3	Who does Sarah trust most in this moment?	deeper	f
4	4	What should Sarah's next move be?	deepest	f
5	5	Which boy's protection does Sarah value most?	deepest	f
6	6	How should Sarah handle her mother's betrayal?	deepest	f
7	7	What should Sarah choose for her future?	deepest	f
13	17	What's your first impression of Midnight University?	surface	f
14	18	Who is your favorite character so far?	surface	f
\.


--
-- Data for Name: muc_series; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_series (id, slug, title, status, created_at) FROM stdin;
2	new-girl-mystery	The New Girl Mystery	published	2025-09-22 11:10:57.36799+00
\.


--
-- Data for Name: muc_theories; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_theories (id, episode_id, user_id, text, likes, created_at) FROM stdin;
\.


--
-- Data for Name: muc_theory_likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_theory_likes (id, theory_id, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: muc_user_engagement; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_user_engagement (user_id, streak_days, detective_score, last_seen_episode_id) FROM stdin;
647778438	0	20	18
1437934486	0	45	17
\.


--
-- Data for Name: muc_votes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.muc_votes (id, poll_id, option_id, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: naughty_wyr_deliveries; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.naughty_wyr_deliveries (question_id, user_id, delivered_at) FROM stdin;
61	647778438	2025-09-05 14:02:42.316792+00
6	647778438	2025-09-05 14:02:45.027391+00
82	647778438	2025-09-05 14:04:19.340223+00
44	8482725798	2025-09-05 14:04:54.879153+00
19	8482725798	2025-09-05 14:04:57.8224+00
55	647778438	2025-09-05 14:08:58.756339+00
43	647778438	2025-09-05 14:34:36.559234+00
\.


--
-- Data for Name: naughty_wyr_questions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.naughty_wyr_questions (id, question, created_at, system_seed) FROM stdin;
1	Would you rather never have an orgasm again or orgasm every hour on the hour?	2025-09-05 13:59:26.514146+00	t
2	Would you rather only have sex in bed for the rest of your life, or never be able to have sex in bed again?	2025-09-05 13:59:26.514146+00	t
3	Would you rather publish your porn search history or read all your text messages aloud to your hometown?	2025-09-05 13:59:26.514146+00	t
4	Would you rather have a one-night stand or a bubble bath with a stranger?	2025-09-05 13:59:26.514146+00	t
5	Would you rather have sex with someone you hate but the sex is amazing, or have sex with someone you love but the sex is terrible?	2025-09-05 13:59:26.514146+00	t
6	Would you rather always have sex with the lights on, or in a pitch-black room?	2025-09-05 13:59:26.514146+00	t
7	Would you rather never have a good meal again, or never have good sex again?	2025-09-05 13:59:26.514146+00	t
8	Would you rather never have foreplay again or only have foreplay and no penetrative sex of any kind for the rest of your life?	2025-09-05 13:59:26.514146+00	t
9	Would you rather cry every time you climax, or have an orgasm every time you cry?	2025-09-05 13:59:26.514146+00	t
10	Would you rather have a threesome with someone you know or with complete strangers?	2025-09-05 13:59:26.514146+00	t
11	Would you rather have sex with a co-worker or with a high school friend?	2025-09-05 13:59:26.514146+00	t
12	Would you rather be blindfolded or blindfold me?	2025-09-05 13:59:26.514146+00	t
13	Would you rather only have kinky sex or romantic sex?	2025-09-05 13:59:26.514146+00	t
14	Would you rather have morning sex or late-night sex?	2025-09-05 13:59:26.514146+00	t
15	Would you rather give up oral sex or anal sex?	2025-09-05 13:59:26.514146+00	t
16	Would you rather be dominant or submissive in the bedroom?	2025-09-05 13:59:26.514146+00	t
17	Would you rather have sex in the bathroom or the kitchen?	2025-09-05 13:59:26.514146+00	t
18	Would you rather go on top for the rest of your life, or on the bottom?	2025-09-05 13:59:26.514146+00	t
19	Would you rather be a bad kisser or bad at giving oral sex?	2025-09-05 13:59:26.514146+00	t
20	Would you rather only give or only receive?	2025-09-05 13:59:26.514146+00	t
21	Would you rather be tied up or blindfolded?	2025-09-05 13:59:26.514146+00	t
22	Would you rather have sex in a secluded forest or on a secluded beach?	2025-09-05 13:59:26.514146+00	t
23	Would you rather use whipped cream or chocolate syrup during foreplay?	2025-09-05 13:59:26.514146+00	t
24	Would you rather have a spontaneous quickie in a place where we might get caught, or plan an intimate night at home?	2025-09-05 13:59:26.514146+00	t
25	Would you rather incorporate food into our sex life or keep food strictly for dining?	2025-09-05 13:59:26.514146+00	t
26	Would you rather have passionate sex after a fight or make love softly to resolve a conflict?	2025-09-05 13:59:26.514146+00	t
27	Would you rather talk dirty to me over text all day or save it all for when we're together?	2025-09-05 13:59:26.514146+00	t
28	Would you rather wear provocative lingerie or nothing at all under your clothes for a date night?	2025-09-05 13:59:26.514146+00	t
29	Would you rather get a sensual massage with oil or a stimulating massage with a feather?	2025-09-05 13:59:26.514146+00	t
30	Would you rather engage in a role-playing scenario where we are strangers or one where we are historical figures?	2025-09-05 13:59:26.514146+00	t
31	Would you rather incorporate music into our lovemaking or prefer the sounds of nature?	2025-09-05 13:59:26.514146+00	t
32	Would you rather have a steamy session in a hot tub or under a waterfall?	2025-09-05 13:59:26.514146+00	t
33	Would you rather have your hair pulled or your back scratched?	2025-09-05 13:59:26.514146+00	t
34	Would you rather end every date night with a sensual dance or a striptease?	2025-09-05 13:59:26.514146+00	t
35	Would you rather have sex while watching a steamy movie or while listening to seductive music?	2025-09-05 13:59:26.514146+00	t
36	Would you rather have a hushed quickie while guests are in the other room or wait until everyone leaves?	2025-09-05 13:59:26.514146+00	t
37	Would you rather have me speak in an accent during foreplay or stay completely silent but very expressive?	2025-09-05 13:59:26.514146+00	t
38	Would you rather shower together every day or only have bubble baths together on special occasions?	2025-09-05 13:59:26.514146+00	t
39	Would you rather explore new territories with body paint or with blindfolds and sensation play?	2025-09-05 13:59:26.514146+00	t
40	Would you rather make out in the rain or in the backseat of a car?	2025-09-05 13:59:26.514146+00	t
41	Would you rather have me tease you with a feather or with ice cubes?	2025-09-05 13:59:26.514146+00	t
42	Would you rather wake up to oral sex or to a full-body massage?	2025-09-05 13:59:26.514146+00	t
43	Would you rather skinny dip at midnight or sunbathe nude?	2025-09-05 13:59:26.514146+00	t
44	Would you rather playfully wrestle in bed or have a tickle fight?	2025-09-05 13:59:26.514146+00	t
45	Would you rather make love in front of a fireplace or by the light of hundreds of candles?	2025-09-05 13:59:26.514146+00	t
46	Would you rather receive a sexy voicemail or an explicit picture message?	2025-09-05 13:59:26.514146+00	t
47	Would you rather be gently dominated or gently dominate me?	2025-09-05 13:59:26.514146+00	t
48	Would you rather use body chocolate or edible underwear?	2025-09-05 13:59:26.514146+00	t
49	Would you rather explore Kamasutra together or take a steamy couple's yoga class?	2025-09-05 13:59:26.514146+00	t
50	Would you rather have sex in a luxurious hotel room or in a cozy cabin in the woods?	2025-09-05 13:59:26.514146+00	t
51	Would you rather spend an entire day teasing each other without release or have immediate satisfaction?	2025-09-05 13:59:26.514146+00	t
52	Would you rather have your body worshiped or worship my body?	2025-09-05 13:59:26.514146+00	t
53	Would you rather explore light bondage or sensory deprivation?	2025-09-05 13:59:26.514146+00	t
54	Would you rather spend a day sexting or have an hour of uninterrupted phone sex?	2025-09-05 13:59:26.514146+00	t
55	Would you rather play naughty charades or have a sexy scavenger hunt?	2025-09-05 13:59:26.514146+00	t
56	Would you rather be serenaded with a love song before sex or be read erotic poetry after?	2025-09-05 13:59:26.514146+00	t
57	Would you rather have an exotic dancer teach us moves or learn them together from videos?	2025-09-05 13:59:26.514146+00	t
58	Would you rather send me a series of suggestive texts during work hours or a single, very explicit one after hours?	2025-09-05 13:59:26.514146+00	t
59	Would you rather have sex in a cozy tent while camping or in the back of a luxury SUV on a road trip?	2025-09-05 13:59:26.514146+00	t
60	Would you rather explore a fantasy involving food or one involving costumes?	2025-09-05 13:59:26.514146+00	t
61	Would you rather spend a cold day under the covers with me or a hot night under the stars?	2025-09-05 13:59:26.514146+00	t
62	Would you rather seduce me with a strip tease or with a lap dance?	2025-09-05 13:59:26.514146+00	t
63	Would you rather have sex in an elegant, antique chair or on a fluffy, modern rug?	2025-09-05 13:59:26.514146+00	t
64	Would you rather explore light BDSM or have a romantic, rose-petal-covered bed experience?	2025-09-05 13:59:26.514146+00	t
65	Would you rather have me leave sexy notes all over the house or send you provocative emails throughout the day?	2025-09-05 13:59:26.514146+00	t
66	Would you rather have me wear leather or lace?	2025-09-05 13:59:26.514146+00	t
67	Would you rather play a dirty question game or act out a naughty fantasy?	2025-09-05 13:59:26.514146+00	t
68	Would you rather have me write my desires on your body or whisper them in your ear?	2025-09-05 13:59:26.514146+00	t
69	Would you rather have sex with only one position allowed or have sex with no touching allowed?	2025-09-05 13:59:26.514146+00	t
70	Would you rather sneak a kiss in a crowded room or sneak a touch under the table?	2025-09-05 13:59:26.514146+00	t
71	Would you rather make love in front of a mirror or in complete darkness?	2025-09-05 13:59:26.514146+00	t
72	Would you rather leave a hickey where only you can see it or in a place where it's noticeable?	2025-09-05 13:59:26.514146+00	t
73	Would you rather play a sexy truth or dare or a game of erotic hide and seek?	2025-09-05 13:59:26.514146+00	t
74	Would you rather watch your partner masturbate or have your partner watch you masturbate?	2025-09-05 13:59:26.514146+00	t
75	Would you rather switch clothes with your partner or be naked all weekend?	2025-09-05 13:59:26.514146+00	t
76	Would you rather play a game of truth or dare or strip poker?	2025-09-05 13:59:26.514146+00	t
77	Would you rather have really cheesy dirty talk or have completely silent sex?	2025-09-05 13:59:26.514146+00	t
78	Would you rather have sex with your celebrity crush or your high school crush?	2025-09-05 13:59:26.514146+00	t
79	Would you rather hear your neighbors have sex or hear your neighbors have sex?	2025-09-05 13:59:26.514146+00	t
80	Would you rather use sex toys or handcuffs?	2025-09-05 13:59:26.514146+00	t
81	Would you rather reveal your deepest sexual fantasy, or share your most embarrassing sex story?	2025-09-05 13:59:26.514146+00	t
82	Would you rather do OnlyFans together or publish our sex tape?	2025-09-05 13:59:26.514146+00	t
83	Would you rather have a love bite on your neck or on your chest?	2025-09-05 13:59:26.514146+00	t
84	Would you rather sleep with someone who is completely silent or someone who's extremely loud while they have sex?	2025-09-05 13:59:26.514146+00	t
85	Would you rather receive a nude or a dirty text?	2025-09-05 13:59:26.514146+00	t
86	Would you rather try a new sex position or a new sex toy?	2025-09-05 13:59:26.514146+00	t
87	Would you rather watch porn or read erotica?	2025-09-05 13:59:26.514146+00	t
88	Would you rather have sex with your biggest celebrity crush or your favorite porn star?	2025-09-05 13:59:26.514146+00	t
89	Would you rather have a quickie and always orgasm or long passionate sex but never orgasm?	2025-09-05 13:59:26.514146+00	t
90	Would you rather have sex only in darkness or in too bright lighting?	2025-09-05 13:59:26.514146+00	t
91	Would you rather end a first date with sex or with passionate sex?	2025-09-05 13:59:26.514146+00	t
92	Would you rather have your partner only be able to use your hands or their mouth during foreplay?	2025-09-05 13:59:26.514146+00	t
93	Would you rather try pole dancing or lap dancing?	2025-09-05 13:59:26.514146+00	t
94	Would you rather have amazing foreplay or amazing sex? But never both?	2025-09-05 13:59:26.514146+00	t
95	Would you rather suck my toes or have your toes sucked?	2025-09-05 13:59:26.514146+00	t
96	Would you rather make a sex tape or write erotica about us?	2025-09-05 13:59:26.514146+00	t
97	Would you rather use wax play or spanking as foreplay?	2025-09-05 13:59:26.514146+00	t
98	Would you rather lose all sense of touch or all sense of taste?	2025-09-05 13:59:26.514146+00	t
99	Would you rather be bad at foreplay or be bad at sex?	2025-09-05 13:59:26.514146+00	t
100	Would you rather only orgasm once a year or orgasm every time you sneeze?	2025-09-05 13:59:26.514146+00	t
\.


--
-- Data for Name: naughty_wyr_votes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.naughty_wyr_votes (question_id, user_id, choice, voted_at) FROM stdin;
82	647778438	optiona	2025-09-05 14:04:22.230739+00
19	8482725798	optionb	2025-09-05 14:05:01.183695+00
43	647778438	optiona	2025-09-05 14:34:44.96264+00
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.notifications (id, user_id, ntype, actor, post_id, created_at, read, comment_id) FROM stdin;
1	1	post_like	87	3	\N	\N	\N
2	1	post_like	87	5	\N	\N	\N
3	84	post_like	1	11	\N	\N	\N
4	84	comment	1	11	\N	\N	\N
5	2	comment	84	6	\N	\N	\N
6	1	comment	84	5	\N	\N	\N
7	84	comment	1	11	\N	\N	\N
8	2	comment	84	6	\N	\N	\N
9	84	post_like	2	11	\N	\N	\N
10	84	comment	2	11	\N	\N	\N
11	84	post_like	2	10	\N	\N	\N
12	84	comment	2	10	\N	\N	\N
13	1	post_like	2	13	\N	\N	\N
14	1	comment	2	13	\N	\N	\N
15	2	post_like	1	17	\N	\N	\N
16	2	comment	1	17	\N	\N	\N
17	2	comment	1	17	\N	\N	\N
18	1	comment	2	16	\N	\N	\N
19	2	comment	1	17	\N	\N	\N
20	2	comment	1	17	\N	\N	\N
21	1	post_like	2	16	\N	\N	\N
22	2	comment	1	17	\N	\N	\N
23	2	comment	1	17	\N	\N	\N
24	2	comment	1	17	\N	\N	\N
25	2	comment	1	17	\N	\N	\N
26	2	post_like	1	39	\N	\N	\N
27	2	comment	1	39	\N	\N	\N
28	2	comment	1	39	\N	\N	\N
29	2	comment	1	39	\N	\N	\N
30	1	post_like	2	37	\N	\N	\N
31	1	comment	2	37	\N	\N	\N
32	1	comment	2	37	\N	\N	\N
33	2	comment	1	39	\N	\N	\N
34	1	comment	2	37	\N	\N	\N
35	1	post_like	2	36	\N	\N	\N
36	2	comment	1	39	\N	\N	\N
37	2	follow	1	\N	\N	\N	\N
38	2	follow	1	\N	\N	\N	\N
39	2	follow	1	\N	\N	\N	\N
40	2	follow	1	\N	\N	\N	\N
41	2	follow	1	\N	\N	\N	\N
42	2	follow	1	\N	\N	\N	\N
43	1	follow	2	\N	\N	\N	\N
44	1	comment	2	37	\N	\N	\N
45	2	follow	1	\N	\N	\N	\N
46	2	follow	1	\N	\N	\N	\N
47	84	follow	1	\N	\N	\N	\N
48	84	follow	1	\N	\N	\N	\N
49	84	follow	1	\N	\N	\N	\N
50	84	follow	1	\N	\N	\N	\N
51	2	follow	1	\N	\N	\N	\N
52	84	follow	1	\N	\N	\N	\N
53	2	follow	1	\N	\N	\N	\N
54	2	follow	1	\N	\N	\N	\N
55	84	follow	1	\N	\N	\N	\N
56	84	follow	1	\N	\N	\N	\N
57	84	follow	1	\N	\N	\N	\N
58	2	follow	1	\N	\N	\N	\N
59	2	follow	1	\N	\N	\N	\N
60	84	follow	1	\N	\N	\N	\N
61	2	follow	1	\N	\N	\N	\N
62	84	follow	1	\N	\N	\N	\N
63	2	follow	1	\N	\N	\N	\N
64	84	follow	1	\N	\N	\N	\N
65	2	follow	1	\N	\N	\N	\N
\.


--
-- Data for Name: pending_confession_replies; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.pending_confession_replies (id, original_confession_id, replier_user_id, reply_text, created_at, admin_notified, is_voice, voice_file_id, voice_duration) FROM stdin;
10	68	8482725798	Haaye kya baat h	2025-09-12 15:12:53.037555+00	f	f	\N	\N
11	66	647778438	Kya baat hai bhai	2025-09-12 15:34:41.80779+00	f	f	\N	\N
12	68	8482725798	Kya bolti public	2025-09-12 15:35:41.679452+00	f	f	\N	\N
13	68	8482725798	Hayelalad\nD	2025-09-12 15:39:18.868508+00	f	f	\N	\N
18	72	8482725798	Thanx for the reaction	2025-09-12 16:57:26.182802+00	f	f	\N	\N
19	81	1437934486	Hehe nice	2025-09-12 17:00:50.465088+00	f	f	\N	\N
20	64	8482725798	So good	2025-09-12 17:01:03.757773+00	f	f	\N	\N
21	69	647778438	Ohh that's so fucking hot	2025-09-12 17:13:39.425432+00	f	f	\N	\N
\.


--
-- Data for Name: pending_confessions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.pending_confessions (id, author_id, text, created_at, admin_notified, is_voice, voice_file_id, voice_duration) FROM stdin;
\.


--
-- Data for Name: poll_options; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.poll_options (id, poll_id, text) FROM stdin;
1	5	Virat
2	5	Dhoni
3	5	Rohit
4	6	Sachin
5	6	Ganguly
6	7	Sachin
7	7	ganguly
8	8	Tea
9	8	coffee
10	9	Rahul
11	9	modi
12	10	3 idiots
13	10	Taare Zameen par
14	11	Me
15	11	you
16	12	Me
17	12	you
18	13	Me
19	13	you
20	13	you
21	14	I
22	14	you
23	15	Me
24	15	you
25	15	i
\.


--
-- Data for Name: poll_votes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.poll_votes (poll_id, voter_id, option_idx, voted_at) FROM stdin;
7	1437934486	0	2025-09-03 11:49:20.820599+00
5	8482725798	0	2025-09-03 11:49:49.417097+00
8	8482725798	0	2025-09-03 11:55:51.587789+00
9	647778438	1	2025-09-03 19:33:32.099726+00
5	1437934486	2	2025-09-05 12:10:40.137947+00
11	1437934486	0	2025-09-05 12:25:17.264425+00
14	1437934486	0	2025-09-05 12:55:29.664353+00
10	8482725798	0	2025-09-12 09:44:53.794186+00
15	8482725798	1	2025-09-12 09:56:20.824736+00
\.


--
-- Data for Name: polls; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.polls (id, author_id, question, options, created_at, deleted_at) FROM stdin;
6	1437934486	Who is the greatest?	{Sachin,Ganguly}	2025-09-03 11:43:50.571864+00	2025-09-03 11:56:38.455989+00
7	1437934486	Who is the greatest	{Sachin,ganguly}	2025-09-03 11:49:12.318293+00	2025-09-03 11:56:43.751375+00
10	1437934486	Which movie is best?	{"3 idiots","Taare Zameen par"}	2025-09-05 12:10:12.321064+00	\N
13	1437934486	Who is best?	{Me,you,you}	2025-09-05 12:46:13.563299+00	\N
14	1437934486	Who is the best	{I,you}	2025-09-05 12:55:20.323154+00	2025-09-05 12:55:34.444339+00
5	1437934486	Who is the best?	{Virat,Dhoni,Rohit}	2025-09-03 11:42:29.730054+00	2025-09-05 12:56:35.45044+00
8	8482725798	Choose between?	{Tea,coffee}	2025-09-03 11:55:41.890061+00	2025-09-05 12:56:41.997307+00
9	647778438	Who is best?	{Rahul,modi}	2025-09-03 19:33:25.1717+00	2025-09-05 12:56:48.68345+00
11	1437934486	Who is best?	{Me,you}	2025-09-05 12:24:54.923699+00	2025-09-05 12:56:56.022365+00
12	1437934486	Who is the richest?	{Me,you}	2025-09-05 12:25:43.787122+00	2025-09-05 12:57:03.162775+00
15	8482725798	Who is the best test?	{Me,you,i}	2025-09-12 09:56:08.90097+00	2025-09-12 09:56:37.935573+00
\.


--
-- Data for Name: post_likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.post_likes (post_id, user_id, created_at) FROM stdin;
51	647778438	2025-09-24 16:00:01.826306+00
52	647778438	2025-09-24 16:03:35.603437+00
2	228	2025-09-25 11:20:04.756348+00
3	228	2025-09-25 11:41:36.687629+00
5	228	2025-09-25 11:56:18.60526+00
4	228	2025-09-25 12:05:02.403447+00
5	1	2025-09-26 04:28:12.030343+00
4	2	2025-09-26 06:06:52.815378+00
1	1	2025-09-26 07:10:52.193626+00
5	84	2025-09-26 09:04:08.276902+00
5	2	2025-09-26 09:26:32.194553+00
6	84	2025-09-26 10:50:59.694493+00
7	1	2025-09-26 11:03:29.815016+00
8	1	2025-09-26 11:21:47.152289+00
9	2	2025-09-26 11:54:09.238617+00
9	1	2025-09-26 12:54:49.358232+00
8	87	2025-09-26 12:59:51.769176+00
7	87	2025-09-26 13:02:20.761225+00
9	87	2025-09-26 13:03:24.800305+00
3	87	2025-09-26 13:06:43.576992+00
5	87	2025-09-26 13:07:04.294924+00
11	1	2025-09-26 13:25:36.575742+00
11	2	2025-09-26 14:46:59.813165+00
10	2	2025-09-26 15:03:27.964672+00
13	2	2025-09-28 12:16:01.919039+00
17	1	2025-09-28 15:09:38.189637+00
16	2	2025-09-28 16:37:35.741761+00
39	1	2025-09-29 09:47:39.530035+00
37	2	2025-09-29 11:05:46.369923+00
36	2	2025-09-29 11:37:59.109106+00
\.


--
-- Data for Name: post_reports; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.post_reports (id, post_id, user_id, reason, created_at) FROM stdin;
1	39	1	Nudity or sexual content	2025-09-29 13:25:46.938815+00
\.


--
-- Data for Name: posts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.posts (id, author, text, media_url, is_public, created_at) FROM stdin;
\.


--
-- Data for Name: profiles; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.profiles (id, user_id, profile_name, username, bio, avatar_url, is_active) FROM stdin;
3	2	Relationship Goals	Luvsociety	Spread love	\N	t
1	1	Nasty Thing	Luststorm	Here you get all kind of nasty content	\N	f
\.


--
-- Data for Name: qa_answers; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.qa_answers (id, question_id, author_id, text, is_admin, created_at, deleted_at) FROM stdin;
1	1	647778438	Because sab aisa hi hota hai	t	2025-09-03 06:38:57.386079+00	\N
2	1	1437934486	Kuch kar nahi sakte	t	2025-09-03 06:39:54.641341+00	\N
3	1	8482725798	Kya hi bole	f	2025-09-03 06:40:20.801204+00	\N
4	3	8482725798	Hum toh mast h tum batao	f	2025-09-05 12:08:43.822878+00	\N
5	3	1437934486	Mast ekdum tum batao	t	2025-09-05 12:09:13.45656+00	\N
6	6	647778438	Khana khaya aaja\nDaal rice	t	2025-09-12 09:14:53.534149+00	\N
7	6	8482725798	Sabji roti	f	2025-09-12 09:15:30.621601+00	\N
8	7	1437934486	Sab badhiya	t	2025-09-12 09:17:18.096766+00	\N
9	9	647778438	Sab badhiya	t	2025-09-12 09:31:20.846241+00	\N
10	12	1437934486	I am doing good you say	t	2025-09-12 09:41:15.050747+00	\N
11	6	8482725798	Aam puri	f	2025-09-12 09:43:40.398083+00	\N
12	13	8482725798	India	f	2025-09-12 09:58:21.445367+00	\N
\.


--
-- Data for Name: qa_questions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.qa_questions (id, author_id, text, scope, created_at, deleted_at) FROM stdin;
4	\N	What is the best	public	2025-09-12 08:45:15.93304+00	\N
5	\N	What bkev gld	admin	2025-09-12 08:47:10.041602+00	\N
6	\N	Kya khaya aaj	public	2025-09-12 09:14:32.197884+00	\N
7	\N	Kya haal hai admin	admin	2025-09-12 09:15:55.592464+00	\N
8	647778438	Kya haal hai chote	public	2025-09-12 09:24:35.916285+00	2025-09-12 09:25:50.087003+00
9	647778438	Whatsup guys	public	2025-09-12 09:31:10.227582+00	2025-09-12 09:31:30.618064+00
10	8482725798	What's ur name?	public	2025-09-12 09:32:02.141597+00	\N
12	8482725798	Hey admin how are you?	admin	2025-09-12 09:40:26.855413+00	2025-09-12 09:41:31.610148+00
2	\N	Whatsup guys?	public	2025-09-03 11:15:39.533033+00	2025-09-12 09:42:28.701819+00
3	\N	Hello guys kaisa hai aap?	public	2025-09-05 12:08:08.253599+00	2025-09-12 09:42:38.841805+00
1	\N	Why so many things happen	public	2025-09-03 04:56:30.743233+00	2025-09-12 09:42:51.898521+00
11	8482725798	You are from?	admin	2025-09-12 09:32:12.83184+00	2025-09-12 09:43:05.652106+00
13	8482725798	Who will win today?	public	2025-09-12 09:57:57.18129+00	\N
14	8482725798	Who will win today?	admin	2025-09-12 09:58:06.259114+00	2025-09-12 09:58:44.012648+00
\.


--
-- Data for Name: referrals; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.referrals (inviter_id, invitee_id, rewarded, added_at) FROM stdin;
\.


--
-- Data for Name: reports; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.reports (id, reporter, target, reason, created_at) FROM stdin;
\.


--
-- Data for Name: secret_chats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.secret_chats (id, a, b, created_at, expires_at, closed_at) FROM stdin;
\.


--
-- Data for Name: secret_crush; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.secret_crush (user_id, target_id, created_at) FROM stdin;
8482725798	647778438	2025-09-02 07:11:35.180466+00
647778438	8482725798	2025-09-02 07:12:00.273263+00
8482725798	1437934486	2025-09-02 14:06:22.87779+00
647778438	1437934486	2025-09-15 09:49:19.989255+00
1437934486	647778438	2025-09-15 09:50:19.636477+00
1437934486	8482725798	2025-09-15 09:59:03.795018+00
\.


--
-- Data for Name: sensual_reactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.sensual_reactions (id, story_id, user_id, reaction, created_at) FROM stdin;
\.


--
-- Data for Name: sensual_stories; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.sensual_stories (id, title, content, category, created_at, is_featured) FROM stdin;
\.


--
-- Data for Name: social_comments; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.social_comments (id, post_id, user_tg_id, text, created_at) FROM stdin;
\.


--
-- Data for Name: social_friend_requests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.social_friend_requests (id, requester_tg_id, target_tg_id, status, created_at) FROM stdin;
\.


--
-- Data for Name: social_friends; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.social_friends (id, user_tg_id, friend_tg_id, created_at) FROM stdin;
\.


--
-- Data for Name: social_likes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.social_likes (id, post_id, user_tg_id, created_at) FROM stdin;
\.


--
-- Data for Name: social_posts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.social_posts (id, author_tg_id, text, media, is_public, created_at) FROM stdin;
\.


--
-- Data for Name: social_profiles; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.social_profiles (id, tg_user_id, username, bio, photo, privacy, show_fields, created_at) FROM stdin;
\.


--
-- Data for Name: stories; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.stories (id, author_id, kind, text, media_id, created_at, expires_at) FROM stdin;
9	0	official	Welcome to LuvHive Stories! ✨	\N	2025-09-30 09:06:22.958733+00	2026-09-30 08:40:03.248363+00
10	1	user	\N	BQACAgUAAyEGAAS7uGd-AANBaNuyuZIzgXJl3TbmSgbgVvUNwCgAArwbAAItu-FW-4S1QfviOTs2BA	2025-09-30 10:36:37.481547+00	2025-10-01 10:36:37.481547+00
11	1	user	\N	BQACAgUAAyEGAAS7uGd-AANCaNu274u8uYhpivghykESCpa3cUQAAswbAAItu-FWnBNRxvjJUp82BA	2025-09-30 10:54:36.733607+00	2025-10-01 10:54:36.733607+00
12	1	user	\N	BQACAgUAAyEGAAS7uGd-AANDaNvMnHEKLFX93O5p7ybiENctgyIAAg4cAAItu-FWNRc7gKpfGJc2BA	2025-09-30 12:27:04.574907+00	2025-10-01 12:27:04.574907+00
13	1	user	\N	BQACAgUAAyEGAAS7uGd-AANEaNvNdhStyeiLP1LzSx_ts0RL-xsAAhAcAAItu-FWmTcRVaG6GxU2BA	2025-09-30 12:30:44.343895+00	2025-10-01 12:30:44.343895+00
14	1	user	\N	BQACAgUAAyEGAAS7uGd-AANFaNvNhA9Hg6F-37sEomgpppcQZOkAAhEcAAItu-FWzyXjPJ8vBeE2BA	2025-09-30 12:30:58.088368+00	2025-10-01 12:30:58.088368+00
15	1	user	\N	BQACAgUAAyEGAAS7uGd-AANGaNzRrRf18XanJruBG2jBcF-a-_IAAqwbAAItu-lWLLp3QHBxsIA2BA	2025-10-01 07:00:57.56966+00	2025-10-02 07:00:57.56966+00
\.


--
-- Data for Name: story_segments; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.story_segments (id, story_id, segment_type, content_type, file_id, text, created_at, user_id, profile_id) FROM stdin;
\.


--
-- Data for Name: story_views; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.story_views (id, story_id, user_id, viewed_at) FROM stdin;
1	9	2	2025-09-30 09:33:43.357801+00
18	9	1	2025-09-30 09:39:26.46041+00
29	9	84	2025-09-30 10:03:27.046946+00
60	10	1	2025-09-30 10:54:27.137834+00
63	11	1	2025-09-30 11:59:45.43446+00
72	12	1	2025-09-30 12:30:02.91207+00
84	13	1	2025-10-01 06:48:11.821074+00
91	15	1	2025-10-01 07:22:06.200697+00
\.


--
-- Data for Name: user_badges; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_badges (user_id, badge_id, earned_at) FROM stdin;
1437934486	premium_supporter	2025-09-03 18:20:10.295+00
1437934486	early_user	2025-09-03 18:20:11.011273+00
647778438	premium_supporter	2025-09-03 19:32:54.262725+00
647778438	early_user	2025-09-03 19:32:54.506354+00
8482725798	early_user	2025-09-04 21:36:56.160574+00
8482725798	premium_supporter	2025-09-10 07:52:01.387937+00
647778438	verified	2025-09-12 04:33:27.737404+00
8482725798	verified	2025-09-12 04:54:02.416582+00
\.


--
-- Data for Name: user_blocks; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_blocks (blocker_id, blocked_id, created_at) FROM stdin;
\.


--
-- Data for Name: user_follows; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_follows (follower_id, followee_id, created_at) FROM stdin;
84	1	2025-09-26 08:40:50.571504+00
1	84	2025-09-29 15:56:49.937541+00
1	2	2025-09-29 17:53:19.029887+00
\.


--
-- Data for Name: user_interests; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_interests (user_id, interest_key) FROM stdin;
1	intimate
1	anime
1	relationship
1	chatting
1	exchange
1	love
1	friends
1	games
1	vsex
2	vsex
2	anime
2	relationship
2	love
2	friends
2	chatting
2	games
2	intimate
2	exchange
82	friends
82	chatting
82	love
82	anime
82	games
82	relationship
84	friends
84	relationship
84	love
84	anime
84	chatting
84	games
\.


--
-- Data for Name: user_mutes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_mutes (muter_id, muted_id, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.users (id, tg_user_id, gender, age, country, city, is_premium, search_pref, created_at, last_dialog_date, dialogs_total, dialogs_today, messages_sent, messages_recv, rating_up, rating_down, report_count, is_verified, verify_status, verify_method, verify_audio_file, verify_photo_file, verify_phrase, verify_at, verify_src_chat, verify_src_msg, premium_until, language, last_gender_change_at, last_age_change_at, banned_until, banned_reason, banned_by, match_verified_only, incognito, coins, last_daily, strikes, last_strike, spin_last, spins, games_played, bio, photo_file_id, feed_username, feed_is_public, feed_photo, feed_notify, date_of_birth, shadow_banned, shadow_banned_at, min_age_pref, max_age_pref, allow_forward, last_seen, wyr_streak, wyr_last_voted, dare_streak, dare_last_date, vault_tokens, vault_tokens_last_reset, vault_storage_used, vault_coins, display_name, username, avatar_url, is_onboarded, tg_id, active_profile_id) FROM stdin;
152	999002	\N	28	\N	\N	f	any	2025-09-25 07:31:40.144279	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	\N	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-25	0	0	New User	newuser456	\N	t	\N	\N
89	12345	\N	25	\N	\N	f	any	2025-09-24 14:48:32.999678	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	\N	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-24	0	0	Test User	testuser123	\N	t	\N	\N
88	87	Any	25	\N	\N	f	any	2025-09-24 11:36:26.127173	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	user87	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-24	0	0	\N	\N	\N	f	\N	\N
82	1040560837	female	75	London	London	f	any	2025-09-14 06:05:16.392079	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	Never give up ❣️	\N	crazy_doll	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-14	0	0	\N	\N	\N	f	\N	\N
87	123456789	male	25	\N	\N	f	any	2025-09-24 10:47:21.313376	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	\N	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-24	0	0	\N	\N	\N	f	\N	\N
84	8482725798	female	30	India	Mumbai	f	any	2025-09-15 07:26:25.571484	\N	4	4	2	1	0	0	0	t	approved	voice	AwACAgUAAxkBAAJctmjHxSDoC_8yAAEKgLvtQTIxL7ja3AAC1RcAAqrvQFZyAAFFe_zdJtU2BA	\N	Today is 15, code 6545	2025-09-15 07:50:12.560515	8482725798	23734	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	Vidhi	t	\N	t	\N	f	\N	18	99	f	2025-09-27 13:39:00.000198+00	1	2025-09-15	0	\N	10	2025-09-15	0	0	Vikram	vikram_s	https://80b36b2d-922c-49ab-bd43-31b478351840-00-1xprbvjyuj6eq.sisko.replit.dev/api/telefile/BQACAgUAAyEGAAS7uGd-AAMgaNayN0y_nei-n0xcacTN4XOR87UAAtgZAALa0bhWDtCIbR85hUM2BA	t	\N	\N
2	1437934486	male	28	India	Mumbai	t	any	2025-08-27 15:41:29.912503	\N	12	12	3	4	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	2025-09-05 11:42:56.393788	English	2025-09-01 09:46:53.939777+00	2025-09-01 09:47:11.331097+00	\N	\N	\N	f	t	45	2025-09-08 06:45:08.348018+00	0	\N	2025-09-04 09:37:39.790598+00	2	2	Ganpati ❤️❤️❤️	\N	Rajendra	t	\N	t	1995-02-14	f	\N	18	99	f	2025-09-27 06:36:38.752592+00	6	2025-09-17	0	\N	10	2025-09-08	0	30	Siddharth	siddharth14	https://80b36b2d-922c-49ab-bd43-31b478351840-00-1xprbvjyuj6eq.sisko.replit.dev/api/telefile/BQACAgUAAyEGAAS7uGd-AAMjaNa1mJbKoga84lJszZ5vvKjNimsAAuYZAALa0bhWbSdQ0yinbiE2BA	t	\N	3
1	647778438	male	28	India	Mumbai	t	m	2025-08-27 14:44:33.875721	\N	20	20	12	11	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	2025-09-08 10:19:19.633313	\N	2025-09-02 05:43:42.139437+00	2025-09-02 05:44:00.304488+00	\N	\N	\N	f	t	45	2025-09-01 15:39:32.561281+00	0	\N	2025-09-11 06:09:12.896438+00	2	2	Jai Hind 🇮🇳	AgACAgUAAxkBAAJdfWjH3t0-iYO1mjHh4RXWi3yBr-bsAAKCyzEbo8FAVgMbgk-psmaYAQADAgADeQADNgQ	Mangal	t	\N	t	1993-11-01	f	\N	25	30	t	2025-09-26 14:24:26.992068+00	6	2025-09-17	0	\N	10	2025-09-08	0	38	Ganesh	Ganesh14	https://80b36b2d-922c-49ab-bd43-31b478351840-00-1xprbvjyuj6eq.sisko.replit.dev/api/telefile/BQACAgUAAyEGAAS7uGd-AAMlaNfdf8_v__r-Ym6KYx2QVgxA-bQAAt4iAAJ6BcBWJpjz4nX6Ebg2BA	t	\N	\N
261	888888	\N	25	\N	\N	f	any	2025-09-25 10:42:04.148296	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	\N	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-25	0	0	NewUser	newuser888	\N	t	\N	\N
228	999001	\N	28	\N	\N	f	any	2025-09-25 09:23:35.806025	\N	0	0	0	0	0	0	0	f	none	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	f	0	\N	0	\N	\N	0	0	\N	\N	\N	t	\N	t	\N	f	\N	18	99	f	\N	0	\N	0	\N	10	2025-09-25	0	0	Ganesh	ganesh	https://80b36b2d-922c-49ab-bd43-31b478351840-00-1xprbvjyuj6eq.sisko.replit.dev/api/telefile/test123	t	\N	\N
\.


--
-- Data for Name: vault_categories; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.vault_categories (id, name, description, emoji, blur_intensity, premium_only, active, created_at) FROM stdin;
1	Romantic Confessions	Love stories and romantic secrets	💖	75	t	t	2025-09-08 02:13:41.008217+00
2	Dark Secrets	Deep confessions and hidden truths	🖤	85	t	t	2025-09-08 02:13:41.008217+00
3	Midnight Thoughts	Late night revelations	🌙	60	t	t	2025-09-08 02:13:41.008217+00
4	Forbidden Dreams	Fantasies and desires	🔥	90	t	t	2025-09-08 02:13:41.008217+00
5	Funny Confessions	Embarrassing and funny moments	😂	50	t	t	2025-09-08 02:13:41.008217+00
6	Life Lessons	Wisdom and experiences	💡	40	t	t	2025-09-08 02:13:41.008217+00
57	Blur Pictures	Hidden photos and private moments	📸	95	t	t	2025-09-08 02:36:23.582581+00
58	Blur Videos	Secret videos and clips	🎥	95	t	t	2025-09-08 02:36:23.582581+00
\.


--
-- Data for Name: vault_content; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.vault_content (id, submitter_id, category_id, content_text, blurred_text, blur_level, reveal_cost, status, approval_status, approved_by, approved_at, view_count, reveal_count, created_at, updated_at, media_type, file_url, thumbnail_url, blurred_thumbnail_url, file_id) FROM stdin;
482	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-08 20:27:57.563161+00	2025-09-08 20:27:57.563161+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_26.jpg	\N	\N	AgACAgUAAxkBAAJE32i_PEGhjJU2oXct0-sF1X3M4jyHAAILyzEbJxP4Vap1fW9CS--bAQADAgADeAADNgQ
483	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-08 20:27:58.758011+00	2025-09-08 20:27:58.758011+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_19.jpg	\N	\N	AgACAgUAAxkBAAJCg2i-rrrbmPIHNw2kyrnoSPNrTMa6AAKuyTEbJxP4VR4fmtPHuSY7AQADAgADeQADNgQ
481	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-08 20:27:56.365583+00	2025-09-09 06:47:16.593034+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_5.jpg	\N	\N	AgACAgUAAxkBAAJBnWi-iCZW2zzvCsAHEQGu4WYiIvWhAALbyDEbJxP4VanjponrJcPcAQADAgADeAADNgQ
480	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-08 20:27:55.167067+00	2025-09-09 06:47:38.677283+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_16.jpg	\N	\N	AgACAgUAAxkBAAJCgGi-rrrXSJzgLlh1MYdGY-xwjQcEAAKryTEbJxP4VcWKQ84UgD7wAQADAgADeAADNgQ
488	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	3	3	2025-09-08 20:28:04.737182+00	2025-09-09 06:36:49.12421+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_27.jpg	\N	\N	AgACAgUAAxkBAAJE4Gi_PEFt9dii5R7YYz5LM4x_ctzdAAIMyzEbJxP4VXCqgH-DeYWEAQADAgADeQADNgQ
487	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	2	2	2025-09-08 20:28:03.539217+00	2025-09-09 06:37:07.950146+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_25.jpg	\N	\N	AgACAgUAAxkBAAJE2Wi_PEEnwIncR2B3vXIB_NroiW5XAAIIyzEbJxP4VfK0SsmzuJVSAQADAgADeAADNgQ
485	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-08 20:28:01.148529+00	2025-09-09 06:37:46.485007+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_23.jpg	\N	\N	AgACAgUAAxkBAAJE22i_PEF-BcFDA27rP-onQNgsc5SeAAIJyzEbJxP4VVz-q_4pXUuFAQADAgADeQADNgQ
484	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-08 20:27:59.953386+00	2025-09-09 06:38:05.465082+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_18.jpg	\N	\N	AgACAgUAAxkBAAJChmi-rrvhqgaFgP7wrxbKispO1vddAAKwyTEbJxP4VQ5mZ0qcKNwcAQADAgADeAADNgQ
491	8482725798	2	I once lied about why I blocked a friend. I said boundaries. The truth? I envied how loved they were. People text them to hang out; people text me to fix things. I cut them off not to protect myself, but to stop the constant reminder that I am helpful, not chosen.	**Blurred Text** Reveal to read	70	2	pending	approved	\N	\N	1	1	2025-09-08 20:34:24.943872+00	2025-09-09 05:30:00.908355+00	text	\N	\N	\N	\N
524	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-09 06:42:54.492415+00	2025-09-19 07:20:06.458579+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_29.jpg	\N	\N	AgACAgUAAxkBAAJGhWi_zFtmooSrHQ_Jad04BJ1lAAGrxQACwMUxG9KfAAFWaQ2EaIYKTvsBAAMCAAN5AAM2BA
526	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-09 06:43:01.706577+00	2025-09-09 06:43:01.706577+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_33.jpg	\N	\N	AgACAgUAAxkBAAJGgmi_zFq2CtQZaHa8TwX3Cq3MQC-9AAK9xTEb0p8AAVYIJxrgoW6RBAEAAwIAA3kAAzYE
486	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-08 20:28:02.344001+00	2025-09-09 06:25:12.542391+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_24.jpg	\N	\N	AgACAgUAAxkBAAJE3Wi_PEHW7OGkusQZdbLuO4eqMXzzAAIKyzEbJxP4VWbH-5ysvyp9AQADAgADeQADNgQ
490	8482725798	2	I’ve never cheated in a relationship, but I have cheated in grief. I copied sorrow like you copy handwriting—just enough curve to pass the test. People told me how “deep” and “empathetic” I am. I’m not sure there’s anything inside me or if I’m just an echo with perfect timing.	**Blurred Text** Reveal to read	70	2	pending	approved	\N	\N	1	1	2025-09-08 20:34:21.610539+00	2025-09-09 06:26:52.627149+00	text	\N	\N	\N	\N
489	8482725798	2	I didn’t outgrow my self-harm; I outsourced it. I pick partners who will do the damage for me—ignore me, belittle me, love me conditionally—so I can stay clean. When it ends, I call it “bad luck,” post a quote about healing, and pretend I didn’t hand them the knife.	**Blurred Text** Reveal to read	70	2	pending	approved	\N	\N	2	2	2025-09-08 20:34:18.081603+00	2025-09-09 06:27:12.329953+00	text	\N	\N	\N	\N
500	8482725798	5	I flirt by asking for book recommendations and then never reading them. It’s like adopting a plant and naming it “Someday.” My dating life is a library with late fees.	I f███t by as██ng for b██k recom█████tions and t██n n███r re███ng t███. I██s l██e ad████ng a plant and naming it “So████y.” My da██ng l██e is a li███ry w██h late f███.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:27:58.801323+00	2025-09-08 21:27:58.801323+00	text	\N	\N	\N	\N
494	8482725798	4	I fantasize about moving to a city where nobody pronounces my name correctly the first time. I’ll teach them slowly until it sounds like home again—on their tongues and in my chest.	I fan███ize a███t mo██ng to a city w███e no██dy pro████ces my n██e cor███tly the first t███. I’ll t███h t██m sl██ly until it so██ds l██e h██e ag████on their to███es and in my chest.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:26:27.948969+00	2025-09-08 21:26:27.948969+00	text	\N	\N	\N	\N
499	8482725798	5	I left a party without saying goodbye to be mysterious. The next morning my friend texted, “you forgot your coat, your charger, and your mystique.”	I l██t a party wi███ut sa██ng go███ye to be mys█████us. The next mo███ng my fr██nd te███d, “you forgot y██r coat, y██r ch████r, and y██r mys████e.”	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:27:56.69959+00	2025-09-08 21:27:56.69959+00	text	\N	\N	\N	\N
495	8482725798	4	Sometimes I picture pressing “send” on the draft that says: “I never wanted a perfect life. I wanted a life that felt like me.” I don’t send it. Not yet. But the day I do will feel like stepping into sunlight that was always in the room.	Som███mes I pi███re pr████ng “s██d” on the d███t t██t s███: “I n███r wanted a pe███ct life. I wanted a l██e t██t felt l██e me.” I don’t send it. Not y██. ███ the day I do w██l feel l██e st████ng i██o su████ht t██t was al██ys in the room.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:26:31.620871+00	2025-09-08 21:26:31.620871+00	text	\N	\N	\N	\N
493	8482725798	2	I told everyone my burnout was just “tiredness,” but the truth is I fantasized about missing my own birthday so nobody would expect me to perform being okay. The darkness wasn’t dramatic—just slow, boring emptiness that swallowed my hobbies, friendships, and even my voice. I smiled in photos while Googling “how to disappear without dying.” The scariest part wasn’t wanting to end it; it was accepting a version of me that didn’t mind never feeling anything again.	**Blurred Text** Reveal to read	70	2	pending	approved	\N	\N	6	6	2025-09-08 20:34:30.412303+00	2025-09-12 11:21:17.909265+00	text	\N	\N	\N	\N
492	8482725798	2	I keep the light on when I sleep because silence makes me hear my father’s advice in my head—every word a rule I never agreed to. I’m a grown adult who still hides receipts like a teenager because I’m terrified of being “financially irresponsible” in a house I pay for. I’m free on paper, but my mind still asks for permission to buy toothpaste.	**Blurred Text** Reveal to read	70	2	pending	approved	\N	\N	2	2	2025-09-08 20:34:28.503279+00	2025-09-13 05:16:14.690631+00	text	\N	\N	\N	\N
496	8482725798	4	I want to change my number and tell exactly three people. I want a small life with loud sunsets, a bookshelf that bends, and a partner who calls me in from the balcony because the soup is ready. No announcements. Just two spoons and a shared language	I want to change my nu██er and tell ex███ly t███e pe███e. I want a s███l l██e w██h l██d su████s, a boo███elf t██t be██s, and a pa███er who c███s me in from the ba███ny be███se the s██p is ready. No anno██████nts. J██t ███ spoons and a sh██ed la████ge	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:26:34.947368+00	2025-09-08 21:26:34.947368+00	text	\N	\N	\N	\N
498	8482725798	4	I dream of meeting a stranger on a delayed train and telling the story I denied myself: how we chose the wrong people for the right decades, how we want one reckless chapter before we go back to behaving. One room, two glasses, no names.	I dream of me███ng a st████er on a de███ed t███n and te███ng the story I de██ed my███f: how we c███e the w███g pe██le for the right decades, how we want ███ re████ss ch███er before we go b██k to beh███ng. One r███, ███ gl████s, no na██s.	70	2	pending	approved	\N	\N	1	1	2025-09-08 21:26:44.801566+00	2025-09-09 05:32:16.58937+00	text	\N	\N	\N	\N
497	8482725798	4	I imagine sending a resignation email that’s just a photo of my packed suitcase. I don’t want to be brave on LinkedIn; I want to be a rumor. I rent a room by the sea, sleep until my body forgives me, and let missed calls become fossils.	I imagine se███ng a res█████ion email that’s j██t a p███o of my packed sui███se. I don’t want to be b███e on LinkedIn; I want to be a ru██r. I rent a r██m by the sea, sleep until my b██y fo████es me, and ███ mi██ed c███s be██me fo████s.	70	2	pending	approved	\N	\N	1	1	2025-09-08 21:26:41.458909+00	2025-09-09 05:35:31.953479+00	text	\N	\N	\N	\N
501	8482725798	5	I joined a gym and bought a water bottle so large it could legally pay rent. After two weeks a trainer asked my goals. I said, “to stop paying rent for this bottle.”	I jo██ed a gym and bo██ht a water bo██le so l███e it c███d le███ly pay r███. A███r ███ weeks a tr███er a███d my go██s. I s███, “to s██p pa██ng rent for t██s bo████.”	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:28:02.33315+00	2025-09-08 21:28:02.33315+00	text	\N	\N	\N	\N
510	8482725798	6	I measure progress by maintenance now—how well I treat what I already have. Growth without care is just hoarding.	I me███re pr████ss by maintenance no███ow w██l I t███t w██t I al███dy h███. Gr██th wi███ut c██e is j██t hoa███ng.	70	2	pending	approved	\N	\N	0	0	2025-09-09 02:37:20.256119+00	2025-09-09 02:37:20.256119+00	text	\N	\N	\N	\N
503	8482725798	1	When we kissed, time didn’t stop; it remembered us. I’m not saying you saved me—I’m saying you made staying feel like winning.	When we ki███d, t██e di██’t s███; it rem████red us. I’m not sa██ng ███ s███d me—I’m sa██ng ███ made st███ng feel l██e wi████g.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:32:09.822332+00	2025-09-08 21:32:09.822332+00	text	\N	\N	\N	\N
504	8482725798	1	I don’t want fireworks. I want the ceremony of your Sunday laundry and the sacred geography of your skin. Show me where your shoulders keep their stress; I’ll meet you there with permission and a patient mouth.	I don’t want fir████ks. I want the ce████ny of y██r Su██ay laundry and the sa██ed geo███phy of y██r s███. S██w me w███e y██r sho███ers k██p their st███s; I’ll m██t ███ t███e w██h per████ion and a patient mouth.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:32:13.350163+00	2025-09-08 21:32:13.350163+00	text	\N	\N	\N	\N
505	8482725798	1	The first time you brushed hair from my face, I understood why poets obsess over small weather. It wasn’t dramatic; it was accurate. My whole body agreed with the world, like a hush before rain.	The first t██e ███ br███ed h██r from my f███, I und████ood ███ p███s obsess o██r s███l weather. It wa██’t dra███ic; it was acc███te. My w███e b██y ag██ed w██h the wo██d, l██e a hush before r███.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:32:16.701806+00	2025-09-08 21:32:16.701806+00	text	\N	\N	\N	\N
508	8482725798	6	A friend once told me, “Consistency is love’s most underrated synonym.” Years later the loudest thing I remember isn’t fireworks; it’s a Thursday where they showed up when they were tired. Stability is a kind of romance—quiet, unfashionable, life-saving.	A fr██nd o██e t██d me, “Con████ency is lo██’s m██t und████ted syn███m.” Years l███r the lo███st thing I re████er isn’t fir████ks; it’s a Th████ay w███e they sh██ed up w██n they w██e tired. Sta███ity is a k██d of roma██████iet, unfa██████ble, life-saving.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:33:11.370641+00	2025-09-08 21:33:11.370641+00	text	\N	\N	\N	\N
502	8482725798	5	I practiced a breakup speech for three days and still opened with “thank you for coming to my TED Talk.” He clapped. I bowed. Somewhere there’s a universe where I charged admission.	I pra███ced a br███up sp██ch for t███e d██s and s███l op██ed w██h “t██nk ███ for co██ng to my TED Talk.” He cl████d. I bowed. Som███ere th███’s a un████se w███e I ch███ed adm████on.	70	2	pending	approved	\N	\N	1	1	2025-09-08 21:28:05.692682+00	2025-09-09 02:35:52.944443+00	text	\N	\N	\N	\N
509	8482725798	6	My first boss asked for “a draft, not a masterpiece.” I delivered nothing and called it perfectionism. He said, “Perfectionism is procrastination in a tuxedo.” Most doors open at 70%.	My first boss a███d for “a dr██t, not a mast█████ce.” I del███red no███ng and ca██ed it perf██████ism. He s███, “Per██████nism is procr█████ation in a tu████.” M██t d███s o██n at 70%.	70	2	pending	approved	\N	\N	2	2	2025-09-08 21:33:13.461648+00	2025-09-09 06:38:48.136567+00	text	\N	\N	\N	\N
507	8482725798	1	I fell for you the day we walked a little slower on purpose. Your hand didn’t reach for mine; it hovered, as if getting to touch me was a promise worth savoring. Ordinary things became artifacts because you were near; even streetlights felt like soft moons we privately owned.	I fell for ███ the day we wa██ed a li██le sl██er on pu████e. Y██r h██d di██’t reach for m███; it ho████d, as if getting to touch me was a pr███se w███h sav███ng. Or████ry things became art███cts be███se ███ w██e near; even stre████ghts felt l██e soft m███s we pri███ely owned.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:32:22.149098+00	2025-09-08 21:32:22.149098+00	text	\N	\N	\N	\N
506	8482725798	1	Your voice at 11:37 PM is my favorite place—not your words, but your exhale before the story. Desire is easy; devotion is the quiet choreography I’m hungry for: the grocery list we build on Tuesday, the spot on your shoulder that fits my forehead like it was measured there.	Y██r v███e at 11:37 PM is my fa████te pla███not y██r words, ███ y██r ex██le before the story. De██re is e███; de████on is the q███t chor████aphy I’m hu██ry f██: the gr███ry list we b███d on Tu████y, the s██t on y██r sh████er t██t f██s my fo████ad l██e it was me████ed th██e.	70	2	pending	approved	\N	\N	0	0	2025-09-08 21:32:20.247385+00	2025-09-08 21:32:20.247385+00	text	\N	\N	\N	\N
527	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-09 06:43:05.329497+00	2025-09-09 06:43:05.329497+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_34.jpg	\N	\N	AgACAgUAAxkBAAJGg2i_zFop0s9ni3R_5u5EyVC1j-mGAAK-xTEb0p8AAVYz1cTqUwf6zwEAAwIAA3kAAzYE
525	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-09 06:42:58.099556+00	2025-09-09 06:42:58.099556+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_31.jpg	\N	\N	AgACAgUAAxkBAAJGhmi_zFtRJTXZS-CrBYu2Dw0E9j0xAALBxTEb0p8AAVaNzIJQx9F-KgEAAwIAA3kAAzYE
513	8482725798	3	I keep a note called “reasons to keep going.” It has groceries mixed with goals: dish soap, call mom, finish chapter two, learn to rest without quitting. Survival is mundane. That’s okay.	I keep a n██e ca██ed “r████ns to keep go███.” It has groceries mixed w██h go██s: d██h s███, c██l mom, finish ch███er two, learn to rest wi███ut qui███ng. Su████al is mu████e. Th██’s o███.	70	2	pending	approved	\N	\N	0	0	2025-09-09 02:42:17.007225+00	2025-09-09 02:42:17.007225+00	text	\N	\N	\N	\N
514	8482725798	3	I wonder how many friendships I could resurrect with one brave text. Not a paragraph—just “hey, I miss you.”	I wonder how m██y fri█████ips I c███d res███ect w██h ███ b███e t███. Not a paragraph—just “hey, I m██s you.”	70	2	pending	approved	\N	\N	0	0	2025-09-09 02:42:20.628954+00	2025-09-09 02:42:20.628954+00	text	\N	\N	\N	\N
516	8482725798	3	Midnight is when courage puts on pajamas. You won’t start the novel now, but you will admit you want to. The wanting is honest in the dark. It’s enough for tonight.	Mi████ht is w██n co███ge p██s on pa████s. ███ won’t start ███ novel n██, but ███ w██l a███t ███ w██t to. The wa███ng is ho██st in ███ d███. I██s en██gh for to████t.	70	2	pending	approved	\N	\N	0	0	2025-09-09 02:42:27.495557+00	2025-09-09 02:42:27.495557+00	text	\N	\N	\N	\N
515	8482725798	3	Sometimes the group chat goes quiet and your brain becomes an emergency meeting. Then the sun arrives and your inner board resigns. Morning is merciful like that.	Som███mes ███ g███p c██t goes q███t and y██r b███n be███es an eme███ncy me████g. T██n ███ ███ ar███es and y██r inner b███d re████s. Mo███ng is me████ul like t███.	70	2	pending	approved	\N	\N	0	0	2025-09-09 02:42:23.968281+00	2025-09-09 02:42:23.968281+00	text	\N	\N	\N	\N
522	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-09 06:42:47.292811+00	2025-09-09 06:42:47.292811+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_30.jpg	\N	\N	AgACAgUAAxkBAAJGgWi_zFp64F0x1YYcYuBnvQ8PLCvcAAK8xTEb0p8AAVYo_Qs9bLQlOwEAAwIAA3gAAzYE
523	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-09 06:42:50.891721+00	2025-09-09 06:42:50.891721+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_32.jpg	\N	\N	AgACAgUAAxkBAAJGhGi_zFo1FQiunQq9o5c03JnKMbgQAAK_xTEb0p8AAVb90-iXO298iAEAAwIAA3kAAzYE
517	8482725798	3	Do you ever sit in the glow of the fridge at 1:13 AM and realize most of your life is a collection of rooms you left too quickly? Commitment isn’t a cage; it’s a view that appears after the first hour of discomfort.	Do ███ e██r ███ in ███ g██w of ███ fr██ge at 1:13 AM and realize m██t of y██r l██e is a collection of r███s ███ l██t ███ qu████y? Com████ent i███t a cage; it’s a v██w t██t ap███rs a███r ███ first h██r of dis█████rt.	70	2	pending	approved	\N	\N	1	1	2025-09-09 02:42:29.405598+00	2025-09-09 05:36:51.132875+00	text	\N	\N	\N	\N
520	8482725798	58	🎥 Submitted Video	🌫️ **Blurred Video** — Reveal to watch	95	4	pending	approved	\N	\N	2	2	2025-09-09 03:56:08.481621+00	2025-09-09 05:37:48.018286+00	video	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/videos/file_28.mp4	\N	\N	BAACAgUAAxkBAAJF62i_lMNGxuvArG3_1WEyajEnN2M5AAJkGgAC7bL5VQczce3N4WiENgQ
511	8482725798	6	I used to chase closure like a refund. Many stories end mid-sentence. The lesson isn’t “get over it,” it’s “continue anyway.” Your life can be whole while your questions are open.	I u██d to chase cl███re like a re███d. Many st███es end mid-█████nce. The le██on i███t “get o██r it,” it’s “co███nue an████.” Y██r l██e ███ be w███e w███e y██r que███ons ███ open.	70	2	pending	approved	\N	\N	1	1	2025-09-09 02:37:23.765828+00	2025-09-09 06:38:30.500452+00	text	\N	\N	\N	\N
528	1437934486	58	🎥 Submitted Video	🌫️ **Blurred Video** — Reveal to watch	95	4	pending	approved	\N	\N	1	1	2025-09-09 06:51:43.406526+00	2025-09-09 06:57:31.906433+00	video	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/videos/file_35.mp4	\N	\N	BAACAgUAAxkBAAJGu2i_znwwhTP3v-RBnjJrWUkjXGC4AAJ8GAAC0p8AAVano2ezRZZMSjYE
521	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-09 06:42:41.967813+00	2025-09-12 05:43:28.437626+00	image	\N	\N	\N	AgACAgUAAxkBAAJGgGi_zFoKeqTh4idQzYZgB9glTs2SAAK7xTEb0p8AAVZVEJim_icTsgEAAwIAA3kAAzYE
533	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-13 05:13:20.242755+00	2025-09-13 05:13:20.242755+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_40.jpg	\N	\N	AgACAgUAAxkBAAJSQ2jE_Uz6q7-lZUZ5CwlSHb6WY3jaAALKyjEbP7coVnr_91EiJ5lcAQADAgADeQADNgQ
532	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-13 05:13:13.158253+00	2025-09-13 05:13:13.158253+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_39.jpg	\N	\N	AgACAgUAAxkBAAJSQmjE_UzTf8HSWCpLS6i9STptzQ8DAALIyjEbP7coVrJ2Ddt1QObyAQADAgADeQADNgQ
531	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-13 05:13:06.044728+00	2025-09-13 05:13:06.044728+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_38.jpg	\N	\N	AgACAgUAAxkBAAJSQWjE_UyHo_UNa0Gt4qLOU4lWqTqRAALHyjEbP7coVmzOV9eWA9eMAQADAgADeQADNgQ
530	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-13 05:12:58.925178+00	2025-09-13 05:12:58.925178+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_37.jpg	\N	\N	AgACAgUAAxkBAAJSQGjE_UyjA08o68wJyB0wM9GoAeqLAALGyjEbP7coVlDdlPyiuZ9BAQADAgADeAADNgQ
529	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	0	0	2025-09-13 05:12:51.563263+00	2025-09-13 05:12:51.563263+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_36.jpg	\N	\N	AgACAgUAAxkBAAJSP2jE_Uzms4OwmEBA9EjaphJlzIaMAALFyjEbP7coVm0-w4iWbfx5AQADAgADeQADNgQ
534	1437934486	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-13 05:13:27.357579+00	2025-09-19 07:56:43.20937+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_41.jpg	\N	\N	AgACAgUAAxkBAAJSRGjE_Uy_Pa3HBev9SJPglTIOY39cAALLyjEbP7coVginE0EwM68pAQADAgADeQADNgQ
535	647778438	57	📸 Submitted Photo	**Blurred Photo** Reveal for coins	95	3	pending	approved	\N	\N	1	1	2025-09-13 05:23:31.223534+00	2025-09-19 07:20:23.854119+00	image	https://api.telegram.org/file/bot7616389435:AAEA1DLTnQYqDoW9GaakzLdi3bz3bbDF2ws/photos/file_42.jpg	\N	\N	AgACAgUAAxkBAAJSbmjE_9Ak84tso-JuAb9LGrHGax3qAALoxTEbSccpVlV1WdEcVy3rAQADAgADeAADNgQ
537	647778438	2	I've been married for 8 years and everyone thinks we're the perfect couple. They see our Instagram posts, our anniversary celebrations, the way we hold hands in public. What they don't know is that we haven't had a real conversation in over two years. We sleep in the same bed but might as well be strangers. I've memorized his schedule so perfectly that I can avoid being alone with him. When people ask about our "secret" to a happy marriage, I smile and say "communication" while dying inside. The truth is, we're both too scared to admit we fell out of love years ago. We're living parallel lives under the same roof, and I don't even remember what his laugh sounds like anymore. Sometimes I catch him staring at me across the dinner table, and I wonder if he's thinking the same thing - that we're both trapped in a beautiful lie that everyone else envies. The worst part? I'm not even sure I want to fix it anymore.	I've been ma███ed for 8 years ███ ev████ne th██ks we're the pe███ct couple. T██y see our Ins███ram po██s, our ann█████ary cele█████ons, the way we hold h███s in public. W██t t██y d███t k██w is that we ha███'t ███ a r██l conv████tion in o██r two ye██s. We sleep in the same ███ but might as w██l be str████rs. I've memorized ███ schedule so per███tly that I ███ a███d being alone w██h h██. W██n pe██le ask a███t our "s████t" to a happy mar███ge, I s███e ███ say "comm█████tion" w███e d███g in███e. The t███h is, we're b██h ███ sc██ed to admit we f██l out of l██e years ago. W███e li██ng parallel l███s under the same r███, ███ I d███t e██n re████er w██t ███ laugh so██ds l██e an████e. Som███mes I catch him st███ng at me across the di██er ta██e, ███ I wo██er if he's th████ng the same t███g - that we're b██h tr███ed in a beautiful ███ that ev████ne e██e envies. The worst p███? I'm not e██n sure I w██t to ███ it an████e.	70	2	pending	approved	\N	\N	1	1	2025-09-16 15:35:43.339021+00	2025-09-19 07:57:10.282437+00	text	\N	\N	\N	\N
\.


--
-- Data for Name: vault_daily_category_views; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.vault_daily_category_views (id, user_id, category_id, views_today, view_date, created_at, updated_at) FROM stdin;
89	8482725798	6	4	2025-09-09	2025-09-09 02:36:26.434767+00	2025-09-09 06:38:33.307834+00
123	1437934486	57	3	2025-09-09	2025-09-09 06:36:34.944926+00	2025-09-09 06:41:43.186987+00
21	647778438	57	36	2025-09-08	2025-09-08 09:37:14.13707+00	2025-09-08 13:25:19.185854+00
107	8482725798	57	14	2025-09-09	2025-09-09 05:32:50.978576+00	2025-09-09 06:47:41.51893+00
56	8482725798	57	10	2025-09-08	2025-09-08 13:09:03.488888+00	2025-09-08 14:01:40.04388+00
67	1437934486	2	1	2025-09-08	2025-09-08 16:10:38.34393+00	2025-09-08 16:10:38.34393+00
92	8482725798	58	9	2025-09-09	2025-09-09 02:45:08.637385+00	2025-09-09 06:57:46.290769+00
72	8482725798	58	1	2025-09-08	2025-09-08 20:32:57.621574+00	2025-09-08 20:32:57.621574+00
3	1437934486	57	10	2025-09-08	2025-09-08 07:53:47.887404+00	2025-09-08 09:27:36.792782+00
137	8482725798	57	3	2025-09-19	2025-09-19 07:01:29.929338+00	2025-09-19 07:02:01.187291+00
68	8482725798	2	9	2025-09-08	2025-09-08 16:11:53.831659+00	2025-09-08 21:23:46.269663+00
70	8482725798	4	2	2025-09-08	2025-09-08 16:17:28.213009+00	2025-09-08 21:24:20.011572+00
80	8482725798	5	1	2025-09-08	2025-09-08 21:27:42.822556+00	2025-09-08 21:27:42.822556+00
82	8482725798	1	1	2025-09-08	2025-09-08 21:31:56.527722+00	2025-09-08 21:31:56.527722+00
81	8482725798	6	2	2025-09-08	2025-09-08 21:29:36.527339+00	2025-09-08 21:32:59.784321+00
86	8482725798	1	1	2025-09-09	2025-09-09 02:34:19.114651+00	2025-09-09 02:34:19.114651+00
87	8482725798	5	1	2025-09-09	2025-09-09 02:34:32.621187+00	2025-09-09 02:34:32.621187+00
96	1437934486	2	1	2025-09-09	2025-09-09 04:35:40.402429+00	2025-09-09 04:35:40.402429+00
85	8482725798	4	5	2025-09-09	2025-09-09 02:33:59.122666+00	2025-09-09 05:35:43.893306+00
88	8482725798	3	4	2025-09-09	2025-09-09 02:36:15.50704+00	2025-09-09 05:36:53.431965+00
84	8482725798	2	11	2025-09-09	2025-09-09 02:33:46.358324+00	2025-09-09 06:26:56.318224+00
\.


--
-- Data for Name: vault_daily_limits; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.vault_daily_limits (user_id, reveals_used, media_reveals_used, limit_date, premium_status, created_at, updated_at) FROM stdin;
1437934486	0	0	2025-09-08	t	2025-09-08 06:27:39.562027+00	2025-09-08 06:27:39.562027+00
647778438	0	0	2025-09-12	t	2025-09-12 05:43:46.875944+00	2025-09-12 05:43:46.875944+00
\.


--
-- Data for Name: vault_interactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.vault_interactions (id, user_id, content_id, action, tokens_spent, created_at) FROM stdin;
17	8482725798	493	revealed	0	2025-09-09 05:21:45.604278+00
18	8482725798	492	revealed	0	2025-09-09 05:22:31.891154+00
19	8482725798	491	revealed	0	2025-09-09 05:29:59.954057+00
20	8482725798	498	revealed	0	2025-09-09 05:32:15.620631+00
21	8482725798	488	revealed	0	2025-09-09 05:33:57.983662+00
22	8482725798	497	revealed	0	2025-09-09 05:35:31.001089+00
23	8482725798	517	revealed	0	2025-09-09 05:36:50.179902+00
24	8482725798	520	revealed	0	2025-09-09 05:37:47.061312+00
25	8482725798	487	revealed	0	2025-09-09 06:03:03.628528+00
26	8482725798	486	revealed	0	2025-09-09 06:25:11.588537+00
27	8482725798	490	revealed	0	2025-09-09 06:26:51.677104+00
28	8482725798	489	revealed	0	2025-09-09 06:27:11.383428+00
29	1437934486	488	revealed	0	2025-09-09 06:36:48.170405+00
30	1437934486	487	revealed	0	2025-09-09 06:37:07.000506+00
31	8482725798	485	revealed	0	2025-09-09 06:37:45.535619+00
32	8482725798	484	revealed	0	2025-09-09 06:38:04.515773+00
33	8482725798	511	revealed	0	2025-09-09 06:38:29.550893+00
34	8482725798	509	revealed	0	2025-09-09 06:38:47.186692+00
35	8482725798	481	revealed	0	2025-09-09 06:47:15.647746+00
36	8482725798	480	revealed	0	2025-09-09 06:47:37.731718+00
37	8482725798	528	revealed	0	2025-09-09 06:57:30.946979+00
38	647778438	521	revealed	0	2025-09-12 05:43:27.477381+00
39	647778438	493	revealed	0	2025-09-12 11:21:16.949401+00
40	647778438	492	revealed	0	2025-09-13 05:16:13.744086+00
41	8482725798	524	revealed	0	2025-09-19 07:20:05.494448+00
42	8482725798	535	revealed	0	2025-09-19 07:20:22.892835+00
43	8482725798	534	revealed	0	2025-09-19 07:56:42.241499+00
44	8482725798	537	revealed	0	2025-09-19 07:57:09.318699+00
\.


--
-- Data for Name: vault_user_states; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.vault_user_states (user_id, category_id, state, data, created_at) FROM stdin;
\.


--
-- Data for Name: wyr_anonymous_users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_anonymous_users (id, vote_date, tg_user_id, anonymous_name, assigned_at) FROM stdin;
\.


--
-- Data for Name: wyr_group_chats; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_group_chats (vote_date, total_voters, total_messages, is_active, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: wyr_group_messages; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_group_messages (id, vote_date, anonymous_user_id, message_type, content, reply_to_message_id, created_at, is_deleted, deleted_by_admin, deleted_at) FROM stdin;
\.


--
-- Data for Name: wyr_message_reactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_message_reactions (id, message_id, tg_user_id, reaction_type, created_at) FROM stdin;
\.


--
-- Data for Name: wyr_permanent_users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_permanent_users (tg_user_id, permanent_username, assigned_at, total_comments, total_likes, weekly_comments, weekly_likes, last_reset) FROM stdin;
8482725798	User1	2025-09-07 17:04:31.962448+00	5	0	5	0	2025-09-07 17:04:31.962448+00
1437934486	User3	2025-09-07 17:19:28.039829+00	5	0	5	0	2025-09-07 17:19:28.039829+00
647778438	User2	2025-09-07 17:05:28.446464+00	4	0	4	0	2025-09-07 17:05:28.446464+00
\.


--
-- Data for Name: wyr_question_of_day; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_question_of_day (vote_date, a_text, b_text, created_at) FROM stdin;
2025-09-05	Sex with someone you hate but amazing 😈	Sex with someone you love but terrible 💔	2025-09-05 17:34:33.447826+00
2025-09-07	Use food during sex	Use massage oils during sex	2025-09-07 14:45:07.455279+00
2025-09-09	Be remembered as someone's greatest love	Be remembered as someone's best friend	2025-09-09 14:45:08.455489+00
2025-09-10	Sex while watching steamy movie	Sex while listening to seductive music	2025-09-10 14:45:06.146479+00
2025-09-13	Be with someone who challenges you	Be with someone who comforts you	2025-09-13 14:45:08.421792+00
2025-09-15	Always be on top	Always be on the bottom	2025-09-15 14:45:06.172343+00
2025-09-17	Have relationship that's all passion	Have relationship that's all romance	2025-09-17 15:43:48.074404+00
2025-09-20	Be the seducer	Be the one seduced	2025-09-20 14:45:06.111275+00
2025-09-24	Only have sex in bed for life	Never be able to have sex in bed again	2025-09-24 14:45:06.107168+00
2025-09-25	Talk dirty over text all day	Save dirty talk for when together	2025-09-25 14:45:06.275667+00
2025-09-26	Use whipped cream in foreplay	Use chocolate syrup in foreplay	2025-09-26 14:45:33.338398+00
2025-09-28	Make out in the rain	Make out in backseat of car	2025-09-28 14:45:08.869182+00
2025-09-29	Wear provocative lingerie under clothes	Wear nothing under clothes for date	2025-09-29 14:45:06.300361+00
\.


--
-- Data for Name: wyr_votes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wyr_votes (tg_user_id, vote_date, side, created_at) FROM stdin;
8482725798	2025-09-05	A	2025-09-05 17:47:55.409526+00
1437934486	2025-09-05	A	2025-09-05 17:48:06.033464+00
647778438	2025-09-05	A	2025-09-05 17:28:53.682294+00
647778438	2025-09-07	B	2025-09-07 14:47:59.412094+00
8482725798	2025-09-07	B	2025-09-07 16:17:25.188876+00
1437934486	2025-09-07	B	2025-09-07 14:50:07.166702+00
8482725798	2025-09-10	B	2025-09-10 16:52:33.600084+00
1437934486	2025-09-10	B	2025-09-10 16:59:36.929199+00
647778438	2025-09-10	B	2025-09-10 15:26:26.753491+00
1437934486	2025-09-13	B	2025-09-13 15:07:27.935175+00
8482725798	2025-09-13	A	2025-09-13 14:46:09.929167+00
647778438	2025-09-13	B	2025-09-13 14:45:34.460227+00
8482725798	2025-09-15	B	2025-09-15 15:10:33.742441+00
647778438	2025-09-15	A	2025-09-15 15:26:54.210117+00
1437934486	2025-09-15	B	2025-09-15 15:29:23.745185+00
647778438	2025-09-17	A	2025-09-17 15:44:08.822044+00
1437934486	2025-09-17	A	2025-09-17 15:45:56.268168+00
\.


--
-- Name: ad_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.ad_messages_id_seq', 11, true);


--
-- Name: ad_participants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.ad_participants_id_seq', 8, true);


--
-- Name: ad_prompts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.ad_prompts_id_seq', 49, true);


--
-- Name: ad_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.ad_sessions_id_seq', 6, true);


--
-- Name: chat_extensions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.chat_extensions_id_seq', 1, false);


--
-- Name: chat_ratings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.chat_ratings_id_seq', 50, true);


--
-- Name: chat_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.chat_reports_id_seq', 38, true);


--
-- Name: comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.comments_id_seq', 53, true);


--
-- Name: confession_deliveries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.confession_deliveries_id_seq', 131, true);


--
-- Name: confession_leaderboard_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.confession_leaderboard_id_seq', 1, false);


--
-- Name: confession_reactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.confession_reactions_id_seq', 29, true);


--
-- Name: confession_replies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.confession_replies_id_seq', 31, true);


--
-- Name: confessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.confessions_id_seq', 81, true);


--
-- Name: dare_feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.dare_feedback_id_seq', 1, false);


--
-- Name: dare_responses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.dare_responses_id_seq', 1, false);


--
-- Name: dare_submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.dare_submissions_id_seq', 10, true);


--
-- Name: fantasy_board_reactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_board_reactions_id_seq', 1, false);


--
-- Name: fantasy_chat_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_chat_sessions_id_seq', 1, true);


--
-- Name: fantasy_chats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_chats_id_seq', 1, false);


--
-- Name: fantasy_match_notifs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_match_notifs_id_seq', 78, true);


--
-- Name: fantasy_match_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_match_requests_id_seq', 27, true);


--
-- Name: fantasy_matches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_matches_id_seq', 47, true);


--
-- Name: fantasy_submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.fantasy_submissions_id_seq', 27, true);


--
-- Name: feed_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.feed_comments_id_seq', 13, true);


--
-- Name: feed_posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.feed_posts_id_seq', 39, true);


--
-- Name: friend_chats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.friend_chats_id_seq', 1, false);


--
-- Name: friend_msg_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.friend_msg_requests_id_seq', 1, false);


--
-- Name: likes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.likes_id_seq', 1, false);


--
-- Name: maintenance_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.maintenance_log_id_seq', 1, false);


--
-- Name: miniapp_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.miniapp_comments_id_seq', 1, false);


--
-- Name: miniapp_posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.miniapp_posts_id_seq', 1, false);


--
-- Name: moderation_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.moderation_events_id_seq', 25, true);


--
-- Name: muc_char_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_char_options_id_seq', 16, true);


--
-- Name: muc_char_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_char_questions_id_seq', 4, true);


--
-- Name: muc_char_votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_char_votes_id_seq', 1, false);


--
-- Name: muc_characters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_characters_id_seq', 4, true);


--
-- Name: muc_episodes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_episodes_id_seq', 18, true);


--
-- Name: muc_poll_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_poll_options_id_seq', 51, true);


--
-- Name: muc_polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_polls_id_seq', 14, true);


--
-- Name: muc_series_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_series_id_seq', 2, true);


--
-- Name: muc_theories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_theories_id_seq', 1, true);


--
-- Name: muc_theory_likes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_theory_likes_id_seq', 1, true);


--
-- Name: muc_votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.muc_votes_id_seq', 4, true);


--
-- Name: naughty_wyr_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.naughty_wyr_questions_id_seq', 100, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.notifications_id_seq', 65, true);


--
-- Name: pending_confession_replies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.pending_confession_replies_id_seq', 34, true);


--
-- Name: pending_confessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.pending_confessions_id_seq', 40, true);


--
-- Name: poll_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.poll_options_id_seq', 25, true);


--
-- Name: polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.polls_id_seq', 15, true);


--
-- Name: post_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.post_reports_id_seq', 1, true);


--
-- Name: posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.posts_id_seq', 1, false);


--
-- Name: profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.profiles_id_seq', 4, true);


--
-- Name: qa_answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.qa_answers_id_seq', 12, true);


--
-- Name: qa_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.qa_questions_id_seq', 14, true);


--
-- Name: reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.reports_id_seq', 2, true);


--
-- Name: secret_chats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.secret_chats_id_seq', 1, false);


--
-- Name: sensual_reactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.sensual_reactions_id_seq', 12, true);


--
-- Name: sensual_stories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.sensual_stories_id_seq', 8, true);


--
-- Name: social_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.social_comments_id_seq', 1, false);


--
-- Name: social_friend_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.social_friend_requests_id_seq', 1, false);


--
-- Name: social_friends_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.social_friends_id_seq', 1, false);


--
-- Name: social_likes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.social_likes_id_seq', 1, false);


--
-- Name: social_posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.social_posts_id_seq', 1, false);


--
-- Name: social_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.social_profiles_id_seq', 1, false);


--
-- Name: stories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.stories_id_seq', 15, true);


--
-- Name: story_segments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.story_segments_id_seq', 1, false);


--
-- Name: story_views_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.story_views_id_seq', 102, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.users_id_seq', 4613, true);


--
-- Name: vault_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.vault_categories_id_seq', 1498, true);


--
-- Name: vault_content_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.vault_content_id_seq', 540, true);


--
-- Name: vault_daily_category_views_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.vault_daily_category_views_id_seq', 139, true);


--
-- Name: vault_interactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.vault_interactions_id_seq', 44, true);


--
-- Name: wyr_anonymous_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wyr_anonymous_users_id_seq', 11, true);


--
-- Name: wyr_group_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wyr_group_messages_id_seq', 14, true);


--
-- Name: wyr_message_reactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wyr_message_reactions_id_seq', 7, true);


--
-- Name: ad_messages ad_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_messages
    ADD CONSTRAINT ad_messages_pkey PRIMARY KEY (id);


--
-- Name: ad_participants ad_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_participants
    ADD CONSTRAINT ad_participants_pkey PRIMARY KEY (id);


--
-- Name: ad_prompts ad_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_prompts
    ADD CONSTRAINT ad_prompts_pkey PRIMARY KEY (id);


--
-- Name: ad_sessions ad_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_sessions
    ADD CONSTRAINT ad_sessions_pkey PRIMARY KEY (id);


--
-- Name: blocked_users blocked_users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_pkey PRIMARY KEY (user_id, blocked_uid);


--
-- Name: chat_extensions chat_extensions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chat_extensions
    ADD CONSTRAINT chat_extensions_pkey PRIMARY KEY (id);


--
-- Name: chat_ratings chat_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chat_ratings
    ADD CONSTRAINT chat_ratings_pkey PRIMARY KEY (id);


--
-- Name: chat_reports chat_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chat_reports
    ADD CONSTRAINT chat_reports_pkey PRIMARY KEY (id);


--
-- Name: comment_likes comment_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_pkey PRIMARY KEY (comment_id, user_id);


--
-- Name: comments comments_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


--
-- Name: confession_deliveries confession_deliveries_confession_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_deliveries
    ADD CONSTRAINT confession_deliveries_confession_id_user_id_key UNIQUE (confession_id, user_id);


--
-- Name: confession_deliveries confession_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_deliveries
    ADD CONSTRAINT confession_deliveries_pkey PRIMARY KEY (id);


--
-- Name: confession_leaderboard confession_leaderboard_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_leaderboard
    ADD CONSTRAINT confession_leaderboard_pkey PRIMARY KEY (id);


--
-- Name: confession_leaderboard confession_leaderboard_user_id_period_rank_type_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_leaderboard
    ADD CONSTRAINT confession_leaderboard_user_id_period_rank_type_key UNIQUE (user_id, period, rank_type);


--
-- Name: confession_mutes confession_mutes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_mutes
    ADD CONSTRAINT confession_mutes_pkey PRIMARY KEY (user_id, confession_id);


--
-- Name: confession_reactions confession_reactions_confession_id_user_id_reaction_type_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_reactions
    ADD CONSTRAINT confession_reactions_confession_id_user_id_reaction_type_key UNIQUE (confession_id, user_id, reaction_type);


--
-- Name: confession_reactions confession_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_reactions
    ADD CONSTRAINT confession_reactions_pkey PRIMARY KEY (id);


--
-- Name: confession_replies confession_replies_original_confession_id_replier_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_replies
    ADD CONSTRAINT confession_replies_original_confession_id_replier_user_id_key UNIQUE (original_confession_id, replier_user_id);


--
-- Name: confession_replies confession_replies_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_replies
    ADD CONSTRAINT confession_replies_pkey PRIMARY KEY (id);


--
-- Name: confession_stats confession_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_stats
    ADD CONSTRAINT confession_stats_pkey PRIMARY KEY (user_id);


--
-- Name: confessions confessions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confessions
    ADD CONSTRAINT confessions_pkey PRIMARY KEY (id);


--
-- Name: crush_leaderboard crush_leaderboard_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.crush_leaderboard
    ADD CONSTRAINT crush_leaderboard_pkey PRIMARY KEY (user_id);


--
-- Name: daily_dare_selection daily_dare_selection_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.daily_dare_selection
    ADD CONSTRAINT daily_dare_selection_pkey PRIMARY KEY (dare_date);


--
-- Name: dare_feedback dare_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_feedback
    ADD CONSTRAINT dare_feedback_pkey PRIMARY KEY (id);


--
-- Name: dare_responses dare_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_responses
    ADD CONSTRAINT dare_responses_pkey PRIMARY KEY (id);


--
-- Name: dare_responses dare_responses_user_id_dare_date_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_responses
    ADD CONSTRAINT dare_responses_user_id_dare_date_key UNIQUE (user_id, dare_date);


--
-- Name: dare_stats dare_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_stats
    ADD CONSTRAINT dare_stats_pkey PRIMARY KEY (user_id);


--
-- Name: dare_submissions dare_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_submissions
    ADD CONSTRAINT dare_submissions_pkey PRIMARY KEY (id);


--
-- Name: fantasy_board_reactions fantasy_board_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_board_reactions
    ADD CONSTRAINT fantasy_board_reactions_pkey PRIMARY KEY (id);


--
-- Name: fantasy_board_reactions fantasy_board_reactions_user_id_fantasy_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_board_reactions
    ADD CONSTRAINT fantasy_board_reactions_user_id_fantasy_id_key UNIQUE (user_id, fantasy_id);


--
-- Name: fantasy_chat_sessions fantasy_chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_chat_sessions
    ADD CONSTRAINT fantasy_chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: fantasy_chats fantasy_chats_chat_room_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_chats
    ADD CONSTRAINT fantasy_chats_chat_room_id_key UNIQUE (chat_room_id);


--
-- Name: fantasy_chats fantasy_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_chats
    ADD CONSTRAINT fantasy_chats_pkey PRIMARY KEY (id);


--
-- Name: fantasy_match_notifs fantasy_match_notifs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_match_notifs
    ADD CONSTRAINT fantasy_match_notifs_pkey PRIMARY KEY (id);


--
-- Name: fantasy_match_requests fantasy_match_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_match_requests
    ADD CONSTRAINT fantasy_match_requests_pkey PRIMARY KEY (id);


--
-- Name: fantasy_matches fantasy_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_matches
    ADD CONSTRAINT fantasy_matches_pkey PRIMARY KEY (id);


--
-- Name: fantasy_stats fantasy_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_stats
    ADD CONSTRAINT fantasy_stats_pkey PRIMARY KEY (fantasy_id);


--
-- Name: fantasy_submissions fantasy_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_submissions
    ADD CONSTRAINT fantasy_submissions_pkey PRIMARY KEY (id);


--
-- Name: feed_comments feed_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_comments
    ADD CONSTRAINT feed_comments_pkey PRIMARY KEY (id);


--
-- Name: feed_likes feed_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_likes
    ADD CONSTRAINT feed_likes_pkey PRIMARY KEY (post_id, user_id);


--
-- Name: feed_posts feed_posts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_posts
    ADD CONSTRAINT feed_posts_pkey PRIMARY KEY (id);


--
-- Name: feed_profiles feed_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_profiles
    ADD CONSTRAINT feed_profiles_pkey PRIMARY KEY (uid);


--
-- Name: feed_reactions feed_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_reactions
    ADD CONSTRAINT feed_reactions_pkey PRIMARY KEY (post_id, user_id, emoji);


--
-- Name: feed_views feed_views_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_views
    ADD CONSTRAINT feed_views_pkey PRIMARY KEY (post_id, viewer_id);


--
-- Name: friend_chats friend_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friend_chats
    ADD CONSTRAINT friend_chats_pkey PRIMARY KEY (id);


--
-- Name: friend_msg_requests friend_msg_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friend_msg_requests
    ADD CONSTRAINT friend_msg_requests_pkey PRIMARY KEY (id);


--
-- Name: friend_requests friend_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friend_requests
    ADD CONSTRAINT friend_requests_pkey PRIMARY KEY (requester_id, target_id);


--
-- Name: friends friends_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_pkey PRIMARY KEY (user_id, friend_id);


--
-- Name: friendship_levels friendship_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.friendship_levels
    ADD CONSTRAINT friendship_levels_pkey PRIMARY KEY (user1_id, user2_id);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);


--
-- Name: likes likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.likes
    ADD CONSTRAINT likes_pkey PRIMARY KEY (id);


--
-- Name: maintenance_log maintenance_log_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.maintenance_log
    ADD CONSTRAINT maintenance_log_pkey PRIMARY KEY (id);


--
-- Name: miniapp_comments miniapp_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_comments
    ADD CONSTRAINT miniapp_comments_pkey PRIMARY KEY (id);


--
-- Name: miniapp_follows miniapp_follows_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_follows
    ADD CONSTRAINT miniapp_follows_pkey PRIMARY KEY (follower_id, followee_id);


--
-- Name: miniapp_likes miniapp_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_likes
    ADD CONSTRAINT miniapp_likes_pkey PRIMARY KEY (post_id, user_id);


--
-- Name: miniapp_post_views miniapp_post_views_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_post_views
    ADD CONSTRAINT miniapp_post_views_pkey PRIMARY KEY (post_id, user_id);


--
-- Name: miniapp_posts miniapp_posts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_posts
    ADD CONSTRAINT miniapp_posts_pkey PRIMARY KEY (id);


--
-- Name: miniapp_profiles miniapp_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_profiles
    ADD CONSTRAINT miniapp_profiles_pkey PRIMARY KEY (user_id);


--
-- Name: miniapp_profiles miniapp_profiles_username_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_profiles
    ADD CONSTRAINT miniapp_profiles_username_key UNIQUE (username);


--
-- Name: miniapp_saves miniapp_saves_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_saves
    ADD CONSTRAINT miniapp_saves_pkey PRIMARY KEY (post_id, user_id);


--
-- Name: moderation_events moderation_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.moderation_events
    ADD CONSTRAINT moderation_events_pkey PRIMARY KEY (id);


--
-- Name: muc_char_options muc_char_options_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_options
    ADD CONSTRAINT muc_char_options_pkey PRIMARY KEY (id);


--
-- Name: muc_char_questions muc_char_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_questions
    ADD CONSTRAINT muc_char_questions_pkey PRIMARY KEY (id);


--
-- Name: muc_char_votes muc_char_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_votes
    ADD CONSTRAINT muc_char_votes_pkey PRIMARY KEY (id);


--
-- Name: muc_char_votes muc_char_votes_user_id_question_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_votes
    ADD CONSTRAINT muc_char_votes_user_id_question_id_key UNIQUE (user_id, question_id);


--
-- Name: muc_characters muc_characters_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_characters
    ADD CONSTRAINT muc_characters_pkey PRIMARY KEY (id);


--
-- Name: muc_episodes muc_episodes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_episodes
    ADD CONSTRAINT muc_episodes_pkey PRIMARY KEY (id);


--
-- Name: muc_episodes muc_episodes_series_id_idx_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_episodes
    ADD CONSTRAINT muc_episodes_series_id_idx_key UNIQUE (series_id, idx);


--
-- Name: muc_poll_options muc_poll_options_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_poll_options
    ADD CONSTRAINT muc_poll_options_pkey PRIMARY KEY (id);


--
-- Name: muc_polls muc_polls_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_polls
    ADD CONSTRAINT muc_polls_pkey PRIMARY KEY (id);


--
-- Name: muc_series muc_series_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_series
    ADD CONSTRAINT muc_series_pkey PRIMARY KEY (id);


--
-- Name: muc_series muc_series_slug_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_series
    ADD CONSTRAINT muc_series_slug_key UNIQUE (slug);


--
-- Name: muc_theories muc_theories_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theories
    ADD CONSTRAINT muc_theories_pkey PRIMARY KEY (id);


--
-- Name: muc_theory_likes muc_theory_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theory_likes
    ADD CONSTRAINT muc_theory_likes_pkey PRIMARY KEY (id);


--
-- Name: muc_theory_likes muc_theory_likes_theory_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theory_likes
    ADD CONSTRAINT muc_theory_likes_theory_id_user_id_key UNIQUE (theory_id, user_id);


--
-- Name: muc_user_engagement muc_user_engagement_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_user_engagement
    ADD CONSTRAINT muc_user_engagement_pkey PRIMARY KEY (user_id);


--
-- Name: muc_votes muc_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_votes
    ADD CONSTRAINT muc_votes_pkey PRIMARY KEY (id);


--
-- Name: muc_votes muc_votes_user_id_poll_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_votes
    ADD CONSTRAINT muc_votes_user_id_poll_id_key UNIQUE (user_id, poll_id);


--
-- Name: naughty_wyr_deliveries naughty_wyr_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.naughty_wyr_deliveries
    ADD CONSTRAINT naughty_wyr_deliveries_pkey PRIMARY KEY (question_id, user_id);


--
-- Name: naughty_wyr_questions naughty_wyr_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.naughty_wyr_questions
    ADD CONSTRAINT naughty_wyr_questions_pkey PRIMARY KEY (id);


--
-- Name: naughty_wyr_votes naughty_wyr_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.naughty_wyr_votes
    ADD CONSTRAINT naughty_wyr_votes_pkey PRIMARY KEY (question_id, user_id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: pending_confession_replies pending_confession_replies_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_confession_replies
    ADD CONSTRAINT pending_confession_replies_pkey PRIMARY KEY (id);


--
-- Name: pending_confessions pending_confessions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_confessions
    ADD CONSTRAINT pending_confessions_pkey PRIMARY KEY (id);


--
-- Name: poll_options poll_options_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.poll_options
    ADD CONSTRAINT poll_options_pkey PRIMARY KEY (id);


--
-- Name: poll_votes poll_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_pkey PRIMARY KEY (poll_id, voter_id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);


--
-- Name: post_likes post_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_pkey PRIMARY KEY (post_id, user_id);


--
-- Name: post_reports post_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.post_reports
    ADD CONSTRAINT post_reports_pkey PRIMARY KEY (id);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);


--
-- Name: profiles profiles_username_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_username_key UNIQUE (username);


--
-- Name: qa_answers qa_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.qa_answers
    ADD CONSTRAINT qa_answers_pkey PRIMARY KEY (id);


--
-- Name: qa_questions qa_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.qa_questions
    ADD CONSTRAINT qa_questions_pkey PRIMARY KEY (id);


--
-- Name: referrals referrals_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.referrals
    ADD CONSTRAINT referrals_pkey PRIMARY KEY (inviter_id, invitee_id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: secret_chats secret_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.secret_chats
    ADD CONSTRAINT secret_chats_pkey PRIMARY KEY (id);


--
-- Name: secret_crush secret_crush_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.secret_crush
    ADD CONSTRAINT secret_crush_pkey PRIMARY KEY (user_id, target_id);


--
-- Name: sensual_reactions sensual_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sensual_reactions
    ADD CONSTRAINT sensual_reactions_pkey PRIMARY KEY (id);


--
-- Name: sensual_reactions sensual_reactions_story_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sensual_reactions
    ADD CONSTRAINT sensual_reactions_story_id_user_id_key UNIQUE (story_id, user_id);


--
-- Name: sensual_stories sensual_stories_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sensual_stories
    ADD CONSTRAINT sensual_stories_pkey PRIMARY KEY (id);


--
-- Name: social_comments social_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_comments
    ADD CONSTRAINT social_comments_pkey PRIMARY KEY (id);


--
-- Name: social_friend_requests social_friend_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_friend_requests
    ADD CONSTRAINT social_friend_requests_pkey PRIMARY KEY (id);


--
-- Name: social_friends social_friends_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_friends
    ADD CONSTRAINT social_friends_pkey PRIMARY KEY (id);


--
-- Name: social_likes social_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_likes
    ADD CONSTRAINT social_likes_pkey PRIMARY KEY (id);


--
-- Name: social_likes social_likes_post_id_user_tg_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_likes
    ADD CONSTRAINT social_likes_post_id_user_tg_id_key UNIQUE (post_id, user_tg_id);


--
-- Name: social_posts social_posts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_posts
    ADD CONSTRAINT social_posts_pkey PRIMARY KEY (id);


--
-- Name: social_profiles social_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_profiles
    ADD CONSTRAINT social_profiles_pkey PRIMARY KEY (id);


--
-- Name: social_profiles social_profiles_tg_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_profiles
    ADD CONSTRAINT social_profiles_tg_user_id_key UNIQUE (tg_user_id);


--
-- Name: stories stories_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.stories
    ADD CONSTRAINT stories_pkey PRIMARY KEY (id);


--
-- Name: story_segments story_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_segments
    ADD CONSTRAINT story_segments_pkey PRIMARY KEY (id);


--
-- Name: story_views story_views_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_views
    ADD CONSTRAINT story_views_pkey PRIMARY KEY (id);


--
-- Name: story_views story_views_story_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_views
    ADD CONSTRAINT story_views_story_id_user_id_key UNIQUE (story_id, user_id);


--
-- Name: comment_likes unique_comment_user_like; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT unique_comment_user_like UNIQUE (comment_id, user_id);


--
-- Name: story_views unique_story_view; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_views
    ADD CONSTRAINT unique_story_view UNIQUE (story_id, user_id);


--
-- Name: likes uq_like; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.likes
    ADD CONSTRAINT uq_like UNIQUE (post_id, user_id);


--
-- Name: user_badges user_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_pkey PRIMARY KEY (user_id, badge_id);


--
-- Name: user_blocks user_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_blocks
    ADD CONSTRAINT user_blocks_pkey PRIMARY KEY (blocker_id, blocked_id);


--
-- Name: user_follows user_follows_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_pkey PRIMARY KEY (follower_id, followee_id);


--
-- Name: user_mutes user_mutes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_mutes
    ADD CONSTRAINT user_mutes_pkey PRIMARY KEY (muter_id, muted_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_tg_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_tg_id_key UNIQUE (tg_id);


--
-- Name: users users_tg_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_tg_user_id_key UNIQUE (tg_user_id);


--
-- Name: vault_categories vault_categories_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_categories
    ADD CONSTRAINT vault_categories_name_key UNIQUE (name);


--
-- Name: vault_categories vault_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_categories
    ADD CONSTRAINT vault_categories_pkey PRIMARY KEY (id);


--
-- Name: vault_content vault_content_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_content
    ADD CONSTRAINT vault_content_pkey PRIMARY KEY (id);


--
-- Name: vault_daily_category_views vault_daily_category_views_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_daily_category_views
    ADD CONSTRAINT vault_daily_category_views_pkey PRIMARY KEY (id);


--
-- Name: vault_daily_category_views vault_daily_category_views_user_id_category_id_view_date_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_daily_category_views
    ADD CONSTRAINT vault_daily_category_views_user_id_category_id_view_date_key UNIQUE (user_id, category_id, view_date);


--
-- Name: vault_daily_limits vault_daily_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_daily_limits
    ADD CONSTRAINT vault_daily_limits_pkey PRIMARY KEY (user_id);


--
-- Name: vault_interactions vault_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_interactions
    ADD CONSTRAINT vault_interactions_pkey PRIMARY KEY (id);


--
-- Name: vault_interactions vault_interactions_user_id_content_id_action_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_interactions
    ADD CONSTRAINT vault_interactions_user_id_content_id_action_key UNIQUE (user_id, content_id, action);


--
-- Name: vault_user_states vault_user_states_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_user_states
    ADD CONSTRAINT vault_user_states_pkey PRIMARY KEY (user_id);


--
-- Name: wyr_anonymous_users wyr_anonymous_users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_anonymous_users
    ADD CONSTRAINT wyr_anonymous_users_pkey PRIMARY KEY (id);


--
-- Name: wyr_anonymous_users wyr_anonymous_users_vote_date_anonymous_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_anonymous_users
    ADD CONSTRAINT wyr_anonymous_users_vote_date_anonymous_name_key UNIQUE (vote_date, anonymous_name);


--
-- Name: wyr_anonymous_users wyr_anonymous_users_vote_date_tg_user_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_anonymous_users
    ADD CONSTRAINT wyr_anonymous_users_vote_date_tg_user_id_key UNIQUE (vote_date, tg_user_id);


--
-- Name: wyr_group_chats wyr_group_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_group_chats
    ADD CONSTRAINT wyr_group_chats_pkey PRIMARY KEY (vote_date);


--
-- Name: wyr_group_messages wyr_group_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_group_messages
    ADD CONSTRAINT wyr_group_messages_pkey PRIMARY KEY (id);


--
-- Name: wyr_message_reactions wyr_message_reactions_message_id_tg_user_id_reaction_type_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_message_reactions
    ADD CONSTRAINT wyr_message_reactions_message_id_tg_user_id_reaction_type_key UNIQUE (message_id, tg_user_id, reaction_type);


--
-- Name: wyr_message_reactions wyr_message_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_message_reactions
    ADD CONSTRAINT wyr_message_reactions_pkey PRIMARY KEY (id);


--
-- Name: wyr_permanent_users wyr_permanent_users_permanent_username_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_permanent_users
    ADD CONSTRAINT wyr_permanent_users_permanent_username_key UNIQUE (permanent_username);


--
-- Name: wyr_permanent_users wyr_permanent_users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_permanent_users
    ADD CONSTRAINT wyr_permanent_users_pkey PRIMARY KEY (tg_user_id);


--
-- Name: wyr_question_of_day wyr_question_of_day_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_question_of_day
    ADD CONSTRAINT wyr_question_of_day_pkey PRIMARY KEY (vote_date);


--
-- Name: wyr_votes wyr_votes_tg_user_id_vote_date_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_votes
    ADD CONSTRAINT wyr_votes_tg_user_id_vote_date_key UNIQUE (tg_user_id, vote_date);


--
-- Name: comments_one_pinned_per_post; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX comments_one_pinned_per_post ON public.comments USING btree (post_id) WHERE pinned;


--
-- Name: fantasy_match_notifs_unique; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX fantasy_match_notifs_unique ON public.fantasy_match_notifs USING btree (match_id, user_id);


--
-- Name: fcs_a; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fcs_a ON public.fantasy_chat_sessions USING btree (a_id) WHERE (status = 'active'::text);


--
-- Name: fcs_b; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fcs_b ON public.fantasy_chat_sessions USING btree (b_id) WHERE (status = 'active'::text);


--
-- Name: feed_reactions_post_user_idx; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX feed_reactions_post_user_idx ON public.feed_reactions USING btree (post_id, user_id);


--
-- Name: feed_reactions_user_post_idx; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX feed_reactions_user_post_idx ON public.feed_reactions USING btree (user_id, post_id);


--
-- Name: fmr_by_owner; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fmr_by_owner ON public.fantasy_match_requests USING btree (fantasy_owner_id, status);


--
-- Name: fmr_by_request; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fmr_by_request ON public.fantasy_match_requests USING btree (requester_id, status);


--
-- Name: fmr_exp; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fmr_exp ON public.fantasy_match_requests USING btree (expires_at);


--
-- Name: fmr_owner_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fmr_owner_status ON public.fantasy_match_requests USING btree (fantasy_owner_id, status);


--
-- Name: fmr_requester_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX fmr_requester_status ON public.fantasy_match_requests USING btree (requester_id, status);


--
-- Name: idx_conf_delivered_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_conf_delivered_created ON public.confessions USING btree (delivered, created_at);


--
-- Name: idx_conf_seed_deliv_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_conf_seed_deliv_created ON public.confessions USING btree (system_seed, delivered, created_at);


--
-- Name: idx_confession_deliveries_confession; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_confession_deliveries_confession ON public.confession_deliveries USING btree (confession_id);


--
-- Name: idx_confession_deliveries_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_confession_deliveries_user ON public.confession_deliveries USING btree (user_id);


--
-- Name: idx_dare_responses_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_dare_responses_date ON public.dare_responses USING btree (dare_date, response);


--
-- Name: idx_dare_stats_streak; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_dare_stats_streak ON public.dare_stats USING btree (current_streak DESC);


--
-- Name: idx_dare_submissions_approved; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_dare_submissions_approved ON public.dare_submissions USING btree (approved, submission_date);


--
-- Name: idx_fantasy_matches_boy; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_matches_boy ON public.fantasy_matches USING btree (boy_id, status);


--
-- Name: idx_fantasy_matches_boy_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_matches_boy_status ON public.fantasy_matches USING btree (boy_id, status);


--
-- Name: idx_fantasy_matches_girl; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_matches_girl ON public.fantasy_matches USING btree (girl_id, status);


--
-- Name: idx_fantasy_matches_girl_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_matches_girl_status ON public.fantasy_matches USING btree (girl_id, status);


--
-- Name: idx_fantasy_matches_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_matches_status ON public.fantasy_matches USING btree (status, expires_at);


--
-- Name: idx_fantasy_matches_status_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_matches_status_expires ON public.fantasy_matches USING btree (status, expires_at);


--
-- Name: idx_fantasy_submissions_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_submissions_active ON public.fantasy_submissions USING btree (user_id, is_active);


--
-- Name: idx_fantasy_submissions_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_submissions_key ON public.fantasy_submissions USING btree (fantasy_key, is_active);


--
-- Name: idx_fantasy_submissions_user_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_submissions_user_active ON public.fantasy_submissions USING btree (user_id, active);


--
-- Name: idx_fantasy_submissions_vibe_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_fantasy_submissions_vibe_active ON public.fantasy_submissions USING btree (vibe, active) WHERE (active = true);


--
-- Name: idx_miniapp_comments_author; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_comments_author ON public.miniapp_comments USING btree (author_id, created_at DESC);


--
-- Name: idx_miniapp_comments_post_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_comments_post_created ON public.miniapp_comments USING btree (post_id, created_at DESC);


--
-- Name: idx_miniapp_follows_followee_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_follows_followee_status ON public.miniapp_follows USING btree (followee_id, status) WHERE (status = 'approved'::text);


--
-- Name: idx_miniapp_follows_follower_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_follows_follower_status ON public.miniapp_follows USING btree (follower_id, status) WHERE (status = 'approved'::text);


--
-- Name: idx_miniapp_likes_post_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_likes_post_created ON public.miniapp_likes USING btree (post_id, created_at DESC);


--
-- Name: idx_miniapp_likes_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_likes_user ON public.miniapp_likes USING btree (user_id, created_at DESC);


--
-- Name: idx_miniapp_post_views_user_viewed; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_post_views_user_viewed ON public.miniapp_post_views USING btree (user_id, viewed_at DESC);


--
-- Name: idx_miniapp_posts_author_created_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_posts_author_created_id ON public.miniapp_posts USING btree (author_id, created_at DESC, id DESC);


--
-- Name: idx_miniapp_posts_created_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_posts_created_id ON public.miniapp_posts USING btree (created_at DESC, id DESC);


--
-- Name: idx_miniapp_posts_ttl; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_posts_ttl ON public.miniapp_posts USING btree (created_at);


--
-- Name: idx_miniapp_posts_visibility_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_posts_visibility_created ON public.miniapp_posts USING btree (visibility, created_at DESC) WHERE (visibility = 'public'::text);


--
-- Name: idx_miniapp_profiles_username; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_profiles_username ON public.miniapp_profiles USING btree (username) WHERE (username IS NOT NULL);


--
-- Name: idx_miniapp_saves_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_saves_expires ON public.miniapp_saves USING btree (expires_at);


--
-- Name: idx_miniapp_saves_user_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_miniapp_saves_user_expires ON public.miniapp_saves USING btree (user_id, expires_at DESC);


--
-- Name: idx_muc_char_options_question_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_char_options_question_id ON public.muc_char_options USING btree (question_id);


--
-- Name: idx_muc_char_questions_series_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_char_questions_series_id ON public.muc_char_questions USING btree (series_id);


--
-- Name: idx_muc_char_votes_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_char_votes_created_at ON public.muc_char_votes USING btree (created_at);


--
-- Name: idx_muc_char_votes_question_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_char_votes_question_id ON public.muc_char_votes USING btree (question_id);


--
-- Name: idx_muc_char_votes_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_char_votes_user_id ON public.muc_char_votes USING btree (user_id);


--
-- Name: idx_muc_characters_series_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_characters_series_id ON public.muc_characters USING btree (series_id);


--
-- Name: idx_muc_episodes_close_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_episodes_close_at ON public.muc_episodes USING btree (close_at);


--
-- Name: idx_muc_episodes_publish_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_episodes_publish_at ON public.muc_episodes USING btree (publish_at);


--
-- Name: idx_muc_episodes_series_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_episodes_series_status ON public.muc_episodes USING btree (series_id, status);


--
-- Name: idx_muc_episodes_status_publish; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_episodes_status_publish ON public.muc_episodes USING btree (status, publish_at);


--
-- Name: idx_muc_poll_options_poll_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_poll_options_poll_id ON public.muc_poll_options USING btree (poll_id);


--
-- Name: idx_muc_polls_episode_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_polls_episode_id ON public.muc_polls USING btree (episode_id);


--
-- Name: idx_muc_theories_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_theories_created_at ON public.muc_theories USING btree (created_at);


--
-- Name: idx_muc_theories_episode_likes; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_theories_episode_likes ON public.muc_theories USING btree (episode_id, likes DESC);


--
-- Name: idx_muc_user_engagement_detective_score; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_user_engagement_detective_score ON public.muc_user_engagement USING btree (detective_score DESC);


--
-- Name: idx_muc_user_engagement_streak; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_user_engagement_streak ON public.muc_user_engagement USING btree (streak_days DESC);


--
-- Name: idx_muc_votes_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_votes_created_at ON public.muc_votes USING btree (created_at);


--
-- Name: idx_muc_votes_poll_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_votes_poll_id ON public.muc_votes USING btree (poll_id);


--
-- Name: idx_muc_votes_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_muc_votes_user_id ON public.muc_votes USING btree (user_id);


--
-- Name: idx_pending_confessions_admin_notified; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_pending_confessions_admin_notified ON public.pending_confessions USING btree (admin_notified);


--
-- Name: idx_pending_confessions_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_pending_confessions_created_at ON public.pending_confessions USING btree (created_at);


--
-- Name: idx_qa_a; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_qa_a ON public.qa_answers USING btree (question_id, created_at);


--
-- Name: idx_qa_q; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_qa_q ON public.qa_questions USING btree (created_at);


--
-- Name: idx_stories_author; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_stories_author ON public.stories USING btree (author_id);


--
-- Name: idx_stories_exp; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_stories_exp ON public.stories USING btree (expires_at);


--
-- Name: idx_user_blocks_blocked; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_blocks_blocked ON public.user_blocks USING btree (blocked_id);


--
-- Name: idx_user_blocks_blocker; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_blocks_blocker ON public.user_blocks USING btree (blocker_id);


--
-- Name: idx_user_mutes_muted; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_mutes_muted ON public.user_mutes USING btree (muted_id);


--
-- Name: idx_user_mutes_muter; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_mutes_muter ON public.user_mutes USING btree (muter_id);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX idx_users_username ON public.users USING btree (username) WHERE (username IS NOT NULL);


--
-- Name: idx_wyr_anonymous_users_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_wyr_anonymous_users_date ON public.wyr_anonymous_users USING btree (vote_date);


--
-- Name: idx_wyr_anonymous_users_tg_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_wyr_anonymous_users_tg_id ON public.wyr_anonymous_users USING btree (tg_user_id);


--
-- Name: idx_wyr_group_messages_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_wyr_group_messages_created ON public.wyr_group_messages USING btree (created_at DESC);


--
-- Name: idx_wyr_group_messages_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_wyr_group_messages_date ON public.wyr_group_messages USING btree (vote_date);


--
-- Name: idx_wyr_votes_date_side; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_wyr_votes_date_side ON public.wyr_votes USING btree (vote_date, side);


--
-- Name: ix_comments_post_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_comments_post_id ON public.comments USING btree (post_id);


--
-- Name: ix_comments_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_comments_user_id ON public.comments USING btree (user_id);


--
-- Name: ix_likes_post_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_likes_post_id ON public.likes USING btree (post_id);


--
-- Name: ix_likes_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_likes_user_id ON public.likes USING btree (user_id);


--
-- Name: ix_notifications_actor; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notifications_actor ON public.notifications USING btree (actor);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_posts_author; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_posts_author ON public.posts USING btree (author);


--
-- Name: sc_pair_idx; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX sc_pair_idx ON public.secret_chats USING btree (LEAST(a, b), GREATEST(a, b));


--
-- Name: uq_blocked_users_pair; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX uq_blocked_users_pair ON public.blocked_users USING btree (user_id, blocked_uid);


--
-- Name: uq_feed_likes_user_post; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX uq_feed_likes_user_post ON public.feed_likes USING btree (user_id, post_id);


--
-- Name: uq_poll_votes_user_poll; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX uq_poll_votes_user_poll ON public.poll_votes USING btree (voter_id, poll_id);


--
-- Name: ad_messages ad_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_messages
    ADD CONSTRAINT ad_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.ad_sessions(id) ON DELETE CASCADE;


--
-- Name: ad_participants ad_participants_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_participants
    ADD CONSTRAINT ad_participants_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.ad_sessions(id) ON DELETE CASCADE;


--
-- Name: ad_prompts ad_prompts_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ad_prompts
    ADD CONSTRAINT ad_prompts_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.ad_sessions(id) ON DELETE CASCADE;


--
-- Name: comment_likes comment_likes_comment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id) ON DELETE CASCADE;


--
-- Name: comment_likes comment_likes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: comments comments_pinned_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pinned_by_user_id_fkey FOREIGN KEY (pinned_by_user_id) REFERENCES public.users(id);


--
-- Name: confession_deliveries confession_deliveries_confession_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.confession_deliveries
    ADD CONSTRAINT confession_deliveries_confession_id_fkey FOREIGN KEY (confession_id) REFERENCES public.confessions(id);


--
-- Name: dare_feedback dare_feedback_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dare_feedback
    ADD CONSTRAINT dare_feedback_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.dare_submissions(id);


--
-- Name: fantasy_chats fantasy_chats_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_chats
    ADD CONSTRAINT fantasy_chats_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.fantasy_matches(id) ON DELETE CASCADE;


--
-- Name: fantasy_match_notifs fantasy_match_notifs_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_match_notifs
    ADD CONSTRAINT fantasy_match_notifs_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.fantasy_matches(id) ON DELETE CASCADE;


--
-- Name: fantasy_matches fantasy_matches_boy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_matches
    ADD CONSTRAINT fantasy_matches_boy_id_fkey FOREIGN KEY (boy_id) REFERENCES public.users(tg_user_id);


--
-- Name: fantasy_matches fantasy_matches_girl_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_matches
    ADD CONSTRAINT fantasy_matches_girl_id_fkey FOREIGN KEY (girl_id) REFERENCES public.users(tg_user_id);


--
-- Name: fantasy_submissions fantasy_submissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.fantasy_submissions
    ADD CONSTRAINT fantasy_submissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(tg_user_id) ON DELETE CASCADE;


--
-- Name: feed_posts feed_posts_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_posts
    ADD CONSTRAINT feed_posts_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: feed_posts feed_posts_profile_fk; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_posts
    ADD CONSTRAINT feed_posts_profile_fk FOREIGN KEY (profile_id) REFERENCES public.profiles(id) ON DELETE SET NULL;


--
-- Name: feed_comments fk_feed_comments_author; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.feed_comments
    ADD CONSTRAINT fk_feed_comments_author FOREIGN KEY (author_id) REFERENCES public.users(tg_user_id) ON DELETE CASCADE;


--
-- Name: miniapp_comments miniapp_comments_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_comments
    ADD CONSTRAINT miniapp_comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.miniapp_comments(id) ON DELETE CASCADE;


--
-- Name: miniapp_comments miniapp_comments_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_comments
    ADD CONSTRAINT miniapp_comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.miniapp_posts(id) ON DELETE CASCADE;


--
-- Name: miniapp_likes miniapp_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_likes
    ADD CONSTRAINT miniapp_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.miniapp_posts(id) ON DELETE CASCADE;


--
-- Name: miniapp_post_views miniapp_post_views_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_post_views
    ADD CONSTRAINT miniapp_post_views_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.miniapp_posts(id) ON DELETE CASCADE;


--
-- Name: miniapp_saves miniapp_saves_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.miniapp_saves
    ADD CONSTRAINT miniapp_saves_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.miniapp_posts(id) ON DELETE CASCADE;


--
-- Name: muc_char_options muc_char_options_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_options
    ADD CONSTRAINT muc_char_options_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.muc_char_questions(id) ON DELETE CASCADE;


--
-- Name: muc_char_questions muc_char_questions_active_from_episode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_questions
    ADD CONSTRAINT muc_char_questions_active_from_episode_id_fkey FOREIGN KEY (active_from_episode_id) REFERENCES public.muc_episodes(id) ON DELETE SET NULL;


--
-- Name: muc_char_questions muc_char_questions_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_questions
    ADD CONSTRAINT muc_char_questions_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.muc_series(id) ON DELETE CASCADE;


--
-- Name: muc_char_votes muc_char_votes_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_votes
    ADD CONSTRAINT muc_char_votes_option_id_fkey FOREIGN KEY (option_id) REFERENCES public.muc_char_options(id) ON DELETE CASCADE;


--
-- Name: muc_char_votes muc_char_votes_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_char_votes
    ADD CONSTRAINT muc_char_votes_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.muc_char_questions(id) ON DELETE CASCADE;


--
-- Name: muc_characters muc_characters_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_characters
    ADD CONSTRAINT muc_characters_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.muc_series(id) ON DELETE CASCADE;


--
-- Name: muc_episodes muc_episodes_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_episodes
    ADD CONSTRAINT muc_episodes_series_id_fkey FOREIGN KEY (series_id) REFERENCES public.muc_series(id) ON DELETE CASCADE;


--
-- Name: muc_poll_options muc_poll_options_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_poll_options
    ADD CONSTRAINT muc_poll_options_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.muc_polls(id) ON DELETE CASCADE;


--
-- Name: muc_polls muc_polls_episode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_polls
    ADD CONSTRAINT muc_polls_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES public.muc_episodes(id) ON DELETE CASCADE;


--
-- Name: muc_theories muc_theories_episode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theories
    ADD CONSTRAINT muc_theories_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES public.muc_episodes(id) ON DELETE CASCADE;


--
-- Name: muc_theory_likes muc_theory_likes_theory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_theory_likes
    ADD CONSTRAINT muc_theory_likes_theory_id_fkey FOREIGN KEY (theory_id) REFERENCES public.muc_theories(id) ON DELETE CASCADE;


--
-- Name: muc_user_engagement muc_user_engagement_last_seen_episode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_user_engagement
    ADD CONSTRAINT muc_user_engagement_last_seen_episode_id_fkey FOREIGN KEY (last_seen_episode_id) REFERENCES public.muc_episodes(id) ON DELETE SET NULL;


--
-- Name: muc_votes muc_votes_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_votes
    ADD CONSTRAINT muc_votes_option_id_fkey FOREIGN KEY (option_id) REFERENCES public.muc_poll_options(id) ON DELETE CASCADE;


--
-- Name: muc_votes muc_votes_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.muc_votes
    ADD CONSTRAINT muc_votes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.muc_polls(id) ON DELETE CASCADE;


--
-- Name: naughty_wyr_deliveries naughty_wyr_deliveries_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.naughty_wyr_deliveries
    ADD CONSTRAINT naughty_wyr_deliveries_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.naughty_wyr_questions(id) ON DELETE CASCADE;


--
-- Name: naughty_wyr_votes naughty_wyr_votes_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.naughty_wyr_votes
    ADD CONSTRAINT naughty_wyr_votes_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.naughty_wyr_questions(id) ON DELETE CASCADE;


--
-- Name: pending_confession_replies pending_confession_replies_original_confession_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_confession_replies
    ADD CONSTRAINT pending_confession_replies_original_confession_id_fkey FOREIGN KEY (original_confession_id) REFERENCES public.confessions(id) ON DELETE CASCADE;


--
-- Name: poll_options poll_options_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.poll_options
    ADD CONSTRAINT poll_options_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- Name: poll_votes poll_votes_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- Name: post_reports post_reports_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.post_reports
    ADD CONSTRAINT post_reports_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.feed_posts(id) ON DELETE CASCADE;


--
-- Name: post_reports post_reports_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.post_reports
    ADD CONSTRAINT post_reports_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: profiles profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: qa_answers qa_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.qa_answers
    ADD CONSTRAINT qa_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.qa_questions(id) ON DELETE CASCADE;


--
-- Name: sensual_reactions sensual_reactions_story_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sensual_reactions
    ADD CONSTRAINT sensual_reactions_story_id_fkey FOREIGN KEY (story_id) REFERENCES public.sensual_stories(id) ON DELETE CASCADE;


--
-- Name: social_comments social_comments_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_comments
    ADD CONSTRAINT social_comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.social_posts(id) ON DELETE CASCADE;


--
-- Name: social_likes social_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.social_likes
    ADD CONSTRAINT social_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.social_posts(id) ON DELETE CASCADE;


--
-- Name: story_segments story_segments_story_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_segments
    ADD CONSTRAINT story_segments_story_id_fkey FOREIGN KEY (story_id) REFERENCES public.stories(id) ON DELETE CASCADE;


--
-- Name: story_views story_views_story_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_views
    ADD CONSTRAINT story_views_story_id_fkey FOREIGN KEY (story_id) REFERENCES public.stories(id) ON DELETE CASCADE;


--
-- Name: story_views story_views_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.story_views
    ADD CONSTRAINT story_views_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_blocks user_blocks_blocked_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_blocks
    ADD CONSTRAINT user_blocks_blocked_id_fkey FOREIGN KEY (blocked_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_blocks user_blocks_blocker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_blocks
    ADD CONSTRAINT user_blocks_blocker_id_fkey FOREIGN KEY (blocker_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_follows user_follows_followee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_followee_id_fkey FOREIGN KEY (followee_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_follows user_follows_follower_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_follower_id_fkey FOREIGN KEY (follower_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_interests user_interests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_interests
    ADD CONSTRAINT user_interests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_mutes user_mutes_muted_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_mutes
    ADD CONSTRAINT user_mutes_muted_id_fkey FOREIGN KEY (muted_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_mutes user_mutes_muter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_mutes
    ADD CONSTRAINT user_mutes_muter_id_fkey FOREIGN KEY (muter_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: vault_content vault_content_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_content
    ADD CONSTRAINT vault_content_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.vault_categories(id);


--
-- Name: vault_daily_category_views vault_daily_category_views_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_daily_category_views
    ADD CONSTRAINT vault_daily_category_views_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.vault_categories(id);


--
-- Name: vault_interactions vault_interactions_content_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_interactions
    ADD CONSTRAINT vault_interactions_content_id_fkey FOREIGN KEY (content_id) REFERENCES public.vault_content(id) ON DELETE CASCADE;


--
-- Name: vault_user_states vault_user_states_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.vault_user_states
    ADD CONSTRAINT vault_user_states_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.vault_categories(id);


--
-- Name: wyr_group_messages wyr_group_messages_anonymous_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_group_messages
    ADD CONSTRAINT wyr_group_messages_anonymous_user_id_fkey FOREIGN KEY (anonymous_user_id) REFERENCES public.wyr_anonymous_users(id) ON DELETE CASCADE;


--
-- Name: wyr_group_messages wyr_group_messages_reply_to_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_group_messages
    ADD CONSTRAINT wyr_group_messages_reply_to_message_id_fkey FOREIGN KEY (reply_to_message_id) REFERENCES public.wyr_group_messages(id) ON DELETE SET NULL;


--
-- Name: wyr_message_reactions wyr_message_reactions_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wyr_message_reactions
    ADD CONSTRAINT wyr_message_reactions_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.wyr_group_messages(id) ON DELETE CASCADE;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

