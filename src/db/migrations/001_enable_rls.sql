-- Enable RLS + deny-all policies for public schema tables
-- Backend connects via pooler (postgres superuser) — bypasses RLS
-- Data API (anon key) is blocked by deny-all policies

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY deny_all ON public.users FOR ALL USING (false);
CREATE POLICY deny_all ON public.daily_health FOR ALL USING (false);
CREATE POLICY deny_all ON public.activities FOR ALL USING (false);
CREATE POLICY deny_all ON public.devices FOR ALL USING (false);
CREATE POLICY deny_all ON public.chat_conversations FOR ALL USING (false);
CREATE POLICY deny_all ON public.chat_messages FOR ALL USING (false);
CREATE POLICY deny_all ON public.insights FOR ALL USING (false);
