import os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv

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