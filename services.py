import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key) if url and key else None

class SaaSLogger:
    
    @staticmethod
    def check_can_generate(user_id):
        """
        Consulta simples: Usuário existe? É PRO? Tem Créditos?
        Retorna True (Pode usar) ou False (Bloqueado).
        """
        # Se não tiver banco configurado, libera (Modo Dev)
        if not supabase: return True 
        
        try:
            # Busca apenas as colunas necessárias
            response = supabase.table("profiles").select("plan_status, credits_balance").eq("id", user_id).execute()
            data = response.data # Retorna lista [] ou [{'plan_status':...}]
            
            # 1. Se lista vazia, usuário não existe no banco -> Bloqueia
            if not data:
                print(f"🚫 Acesso negado: Usuário '{user_id}' não encontrado.")
                return False

            user = data[0]
            status = user.get('plan_status')
            creditos = user.get('credits_balance', 0)

            # 2. Se for VIP (Admin/Pro), libera geral
            if status in ['pro_monthly', 'pro_annual', 'admin']:
                return True
            
            # 3. Se for FREE, checa saldo
            if status == 'free' and creditos > 0:
                return True
            
            # Se chegou aqui, é Free e sem saldo
            return False

        except Exception as e:
            print(f"⚠️ Erro de conexão ao verificar permissão: {e}")
            return False # Por segurança, bloqueia se o banco der erro crítico

    @staticmethod
    def refresh_free_credits_if_needed(user_id):
        """Reseta créditos FREE com correção de timezone"""
        if not supabase: return

        try:
            response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            if not response.data: return

            user = response.data
            if user["plan_status"] != "free": return

            # CORREÇÃO AQUI: Agora usamos o horário COM fuso UTC
            now = datetime.now(timezone.utc)
            
            should_reset = False
            
            if user["last_credit_reset"] is None:
                should_reset = True
            else:
                # O banco já manda com fuso (+00:00), agora o 'now' também tem. Casamento perfeito.
                last_reset = datetime.fromisoformat(user["last_credit_reset"])
                
                if now - last_reset >= timedelta(hours=24):
                    should_reset = True

            if should_reset:
                supabase.table("profiles").update({
                    "credits_balance": 3,
                    "last_credit_reset": now.isoformat()
                }).eq("id", user_id).execute()
                
        except Exception as e:
            print(f"🔥 ERRO NO RESET: {e}")


    @staticmethod
    def log_generation(user_id, input_text, output_text, model, tokens_in, tokens_out, time_taken):
        """Salva o log de auditoria"""
        if not supabase: return
        
        try:
            supabase.table("generation_logs").insert({
                "user_id": user_id,
                "input_text": input_text,
                "output_text": output_text,
                "model_used": model,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "latency_ms": int(time_taken * 1000),
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            # Log falhou? Printa no terminal mas não trava o app do usuário
            print(f"⚠️ Falha ao salvar log: {e}")

    @staticmethod
    def debit_credit(user_id):
        """Desconta 1 crédito apenas se for plano FREE"""
        if not supabase: return
        
        try:
            # Busca status atual para garantir que não vamos descontar de PRO
            response = supabase.table("profiles").select("plan_status, credits_balance").eq("id", user_id).execute()
            
            if response.data:
                user = response.data[0]
                
                # Só desconta se for FREE e tiver saldo positivo
                if user.get('plan_status') == 'free' and user.get('credits_balance', 0) > 0:
                    novo_saldo = user['credits_balance'] - 1
                    
                    supabase.table("profiles").update({
                        "credits_balance": novo_saldo
                    }).eq("id", user_id).execute()
                    
                    print(f"📉 Crédito debitado de {user_id}. Restam: {novo_saldo}")
        except Exception as e:
            print(f"⚠️ Erro ao debitar crédito: {e}")

    @staticmethod
    def log_event(user_id, event_type, details=None):
        """Registra eventos de sistema (Erros, Logins, etc)"""
        if not supabase: return
        try:
            supabase.table("system_events").insert({
                "user_id": user_id,
                "event_type": event_type,
                "details": str(details),
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except:
            pass

    @staticmethod
    def get_history(user_id, plan_status):
        """Busca o histórico baseado no plano"""
        try:
            # Define o limite de tempo baseado no plano
            if plan_status == 'free':
                time_limit = datetime.utcnow() - timedelta(hours=24)
            else:
                # Plano pago/vitalício: último mês (ou mais, se preferir)
                time_limit = datetime.utcnow() - timedelta(days=30)
            
            # Formata para string ISO compatível com Supabase
            time_limit_str = time_limit.isoformat()

            response = supabase.table("generation_logs")\
                .select("input_text, output_text, created_at")\
                .eq("user_id", user_id)\
                .gte("created_at", time_limit_str)\
                .order("created_at", desc=True)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar histórico: {e}")
            return []

    @staticmethod
    def time_until_next_reset(last_reset_str):
        """Calcula tempo restante com proteção de fuso horário"""
        if not last_reset_str:
            return "agora"

        try:
            # Data do último reset (Vem do banco COM fuso)
            last_reset_dt = datetime.fromisoformat(last_reset_str)
            
            # Próximo reset é +24h
            next_reset = last_reset_dt + timedelta(hours=24)
            
            # CORREÇÃO: Pegamos o 'agora' usando o MESMO fuso da data do banco
            now = datetime.now(last_reset_dt.tzinfo)

            if now >= next_reset:
                return "agora"

            remaining = next_reset - now
            
            total_seconds = int(remaining.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            return f"em {hours}h {minutes}min"
            
        except Exception as e:
            print(f"Erro calculando tempo: {e}")
            return "em breve"

    @staticmethod
    def ensure_credit_reset_initialized(user_id):
        """Garante que last_credit_reset nunca seja NULL"""
        if not supabase:
            return None

        response = supabase.table("profiles") \
            .select("last_credit_reset") \
            .eq("id", user_id) \
            .single() \
            .execute()

        last_reset = response.data.get("last_credit_reset")

        if last_reset is None:
            now_utc = datetime.utcnow().isoformat()

            supabase.table("profiles").update({
                "last_credit_reset": now_utc
            }).eq("id", user_id).execute()

            return now_utc

        return last_reset