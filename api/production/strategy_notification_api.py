from __future__ import annotations
import os
from datetime import datetime
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from .auth import require_permission

router=APIRouter(prefix='/api/v1/strategy/notifications',tags=['Strategy Notification Center'])

def _connect():
    url=os.getenv('DATABASE_URL')
    if not url: raise HTTPException(503,'DATABASE_URL is not configured')
    return psycopg.connect(url)

def _row(r):
    return {'id':r[0],'actionId':r[1],'type':r[2],'title':r[3],'body':r[4],'isRead':r[5],'createdAt':r[6].isoformat() if r[6] else None,'readAt':r[7].isoformat() if r[7] else None}

class ReadUpdate(BaseModel):
    is_read: bool=True

@router.get('')
def notifications(unread_only:bool=Query(False),limit:int=Query(50,ge=1,le=200),principal:dict=Depends(require_permission('strategy.write'))):
    where='WHERE user_id=%s'
    params=[principal['id']]
    if unread_only:
        where+=' AND is_read=FALSE'
    with _connect() as conn,conn.cursor() as cur:
        cur.execute(f'''SELECT id,action_id,notification_type,title,body,is_read,created_at,read_at FROM strategy_notifications {where} ORDER BY created_at DESC LIMIT %s''',(*params,limit))
        rows=cur.fetchall()
        cur.execute('SELECT COUNT(*) FROM strategy_notifications WHERE user_id=%s AND is_read=FALSE',(principal['id'],))
        unread=cur.fetchone()[0]
    return {'unreadCount':unread,'notifications':[_row(r) for r in rows]}

@router.patch('/{notification_id}')
def mark_read(notification_id:int,payload:ReadUpdate,request:Request,principal:dict=Depends(require_permission('strategy.write'))):
    with _connect() as conn,conn.cursor() as cur:
        cur.execute('''UPDATE strategy_notifications SET is_read=%s,read_at=CASE WHEN %s THEN COALESCE(read_at,now()) ELSE NULL END WHERE id=%s AND user_id=%s RETURNING id,action_id,notification_type,title,body,is_read,created_at,read_at''',(payload.is_read,payload.is_read,notification_id,principal['id']))
        row=cur.fetchone()
        if not row: raise HTTPException(404,'Notification not found')
        cur.execute('INSERT INTO eyt_audit_logs(actor_user_id,action,correlation_id,ip_address,metadata) VALUES(%s,%s,%s,%s,%s)',(principal['id'],'strategy.notification.read',request.headers.get('X-Correlation-ID') or os.urandom(8).hex(),request.client.host if request.client else None,{'notification_id':notification_id,'is_read':payload.is_read}))
        conn.commit()
    return _row(row)
