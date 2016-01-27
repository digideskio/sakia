import datetime
import asyncio

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog, QWidget

from ..core.graph import WoTGraph
from ..tools.decorators import asyncify
from ..gen_resources.member_uic import Ui_DialogMember
from ..tools.exceptions import MembershipNotFoundError


class MemberDialog(QObject):
    """
    A widget showing informations about a member
    """

    def __init__(self, app, account, community, identity, widget, ui):
        """
        Init MemberDialog

        :param sakia.core.app.Application app:   Application instance
        :param sakia.core.account.Account account:   Account instance
        :param sakia.core.community.Community community: Community instance
        :param sakia.core.registry.identity.Identity identity: Identity instance
        :param PyQt5.QtWidget widget: The class of the widget
        :param sakia.gen_resources.member_uic.Ui_DialogMember ui: the class of the ui applyed to the widget
        :return:
        """
        super().__init__()
        self.widget = widget
        self.ui = ui
        self.ui.setupUi(self.widget)
        self.app = app
        self.community = community
        self.account = account
        self.identity = identity
        self.ui.label_uid.setText(identity.uid)
        self.refresh()

    @classmethod
    def open_dialog(cls, app, account, community, identity):
        return cls(app, account, community, identity, QDialog(), Ui_DialogMember()).exec()

    @classmethod
    def as_widget(cls, app, account, community, identity):
        return cls(app, account, community, identity, QWidget(), Ui_DialogMember())

    @asyncify
    async def refresh(self):
        try:
            join_date = await self.identity.get_join_date(self.community)
        except MembershipNotFoundError:
            join_date = None

        if join_date is None:
            join_date = self.tr('not a member')
        else:
            join_date = datetime.datetime.fromtimestamp(join_date).strftime("%d/%m/%Y %I:%M")

        # calculate path to account member
        graph = WoTGraph(self.app, self.community)
        path = None
        # if selected member is not the account member...
        if self.identity.pubkey != self.account.pubkey:
            # add path from selected member to account member
            account_identity = await self.account.identity(self.community)
            path = await graph.get_shortest_path_to_identity(self.identity,
                                                            account_identity)

        text = self.tr("""
            <table cellpadding="5">
            <tr><td align="right"><b>{:}</b></div></td><td>{:}</td></tr>
            <tr><td align="right"><b>{:}</b></div></td><td>{:}</td></tr>
            """).format(
            self.tr('Public key'),
            self.identity.pubkey,
            self.tr('Join date'),
            join_date
        )

        if path:
            distance = len(path) - 1
            text += self.tr(
                """<tr><td align="right"><b>{:}</b></div></td><td>{:}</td></tr>"""
                    .format(self.tr('Distance'), distance))
            if distance > 1:
                index = 0
                for node in path:
                    if index == 0:
                        text += self.tr("""<tr><td align="right"><b>{:}</b></div></td><td>{:}</td></tr>""").format(
                            self.tr('Path'), node['text'])
                    else:
                        text += self.tr("""<tr><td align="right"><b>{:}</b></div></td><td>{:}</td></tr>""").format('',
                                                                                                                   node[
                                                                                                                       'text'])
                    if index == distance and node['id'] != self.account.pubkey:
                        text += self.tr("""<tr><td align="right"><b>{:}</b></div></td><td>{:}</td></tr>""").format('',
                                                                                                                   self.account.name)
                    index += 1
        # close html text
        text += "</table>"

        # set text in label
        self.ui.label_properties.setText(text)

    def exec(self):
        self.widget.exec()
