import sqlalchemy as sa

from sosachkino.db.base import Base


class Threads(Base):
    """Model for thread, cleaned up when missing from json."""
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=False)
    board = sa.Column(sa.Text, index=True)
    subject = sa.Column(sa.Text)
    last = sa.Column(sa.Integer)
    files_count = sa.Column(sa.Integer)
    updated = sa.Column(sa.DateTime(timezone=True))
    removed_date = sa.Column(sa.DateTime(timezone=True))


class Files(Base):
    """Webm file model."""
    id = sa.Column(sa.BigInteger, primary_key=True)
    thread = sa.Column(
        sa.ForeignKey('threads.id', onupdate="CASCADE", ondelete="CASCADE"),
        index=True
    )
    timestamp = sa.Column(sa.DateTime(timezone=True), index=True)
    name = sa.Column(sa.Text)
    board = sa.Column(sa.Text, index=True)
    path = sa.Column(sa.Text)
    size = sa.Column(sa.Integer)
    width = sa.Column(sa.Integer)
    height = sa.Column(sa.Integer)
    thumbnail = sa.Column(sa.Text)
    tn_width = sa.Column(sa.Integer)
    tn_height = sa.Column(sa.Integer)
    md5 = sa.Column(sa.Text, index=True)
    hidden = sa.Column(sa.Boolean, default=False)
    last_check = sa.Column(sa.DateTime(timezone=True), default=sa.func.now(),
                           index=True)
