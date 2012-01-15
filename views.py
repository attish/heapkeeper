# This file is part of Heapkeeper.
#
# Heapkeeper is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Heapkeeper is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Heapkeeper.  If not, see <http://www.gnu.org/licenses/>.

# Copyright (C) 2012 Attila Nagy

from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from hk.models import Message, MessageVersion, Conversation, Heap
import datetime

def testgetmsg(request, msg_id):
    message = get_object_or_404(Message, pk=msg_id)
    latest_version = message.latest_version()
    return render_to_response(
            'testgetmsg.html',
            {'msgv': latest_version}
        )

def format_labels(object):
    return '[%s]' % ', '.join([t.text for t in object.labels.all()])

def print_message(l, msg):
    children = msg.get_children()
    edit_url = reverse('hk.views.editmessage', args=(msg.id,))
    l.append("<div class='message'>\n")
    l.append("<a name='message_%d'></a>\n" % msg.id)
    l.append('<h3>\n&lt;%d&gt;\n</h3>\n' % msg.id)
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().author)
    l.append('<h3>\n%s\n</h3>\n' % format_labels(msg.latest_version()))
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().creation_date)
    l.append("<a href='%s'>edit</a>\n" % edit_url)
    l.append('<p>\n%s\n</p>\n' % msg.latest_version().text)
    for child in msg.get_children():
        print_message(l, child)
    l.append('</div>\n')

def conversation(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    root = conv.root_message
    l = []
    print_message(l, root)
    ls = [unicode(m) for m in l]
    return render_to_response(
            'conversation.html',
            {'conv': conv,
             'conv_labels': format_labels(conv),
             'l': '\n'.join(ls)}
        )

def heap(request, heap_id):
    heap = get_object_or_404(Heap, pk=heap_id)
    convs = Conversation.objects.filter(heap=heap)
    return render_to_response(
            'heap.html',
            {'heap': heap,
             'convs': convs}
        )

def heaps(request):
    return render_to_response('heaps.html',
            {'heaps': Heap.objects.all()}
        )

class AddMessageForm(forms.Form):
    parent = forms.IntegerField()
    author = forms.IntegerField()
    text = forms.CharField(widget=forms.Textarea())

def addmessage(request):
    error_message = ''
    form = AddMessageForm()
    if request.method == 'POST':
        form = AddMessageForm(request.POST)
        if form.is_valid():
            # To create a message:
            # - create a message object
            # - create a related message version
            now = datetime.datetime.now()
            msg = Message()
            msg.save()
            mv = MessageVersion(
                    message=Message.objects.get(id=msg.id),
                    parent=Message.objects.get(id=form.cleaned_data['parent']),
                    author=User.objects.get(id=form.cleaned_data['author']),
                    creation_date=now,
                    version_date=now,
                    text=form.cleaned_data['text']
                )
            mv.save()
            error_message = 'Message added.'
            form = AddMessageForm()

    return render_to_response('addmessage.html',
            {'error_message': error_message,
             'form': form},
            context_instance=RequestContext(request))

class EditMessageForm(forms.Form):
    parent = forms.IntegerField(required=False)
    author = forms.IntegerField()
    creation_date = forms.DateTimeField()
    text = forms.CharField(widget=forms.Textarea())


def editmessage(request, msg_id):
    error_message = ''
    m = get_object_or_404(Message, pk=msg_id)
    lv = m.latest_version()
    # Initialize form to fields of latest version
    form = EditMessageForm(initial=
            {
                'creation_date': lv.creation_date,
                'author': lv.author_id,
                'parent': lv.parent_id,
                'text': lv.text
            }
        )
    if request.method == 'POST':
        form = EditMessageForm(request.POST)
        if form.is_valid():
            now = datetime.datetime.now()
            try:
                parent = Message.objects.get(id=form.cleaned_data['parent'])
            except ObjectDoesNotExist:
                parent = None
            mv = MessageVersion(
                    message=Message.objects.get(id=msg_id),
                    parent=parent,
                    author=User.objects.get(id=form.cleaned_data['author']),
                    creation_date=form.cleaned_data['creation_date'],
                    version_date=now,
                    text=form.cleaned_data['text']
                )
            mv.save()
            error_message = 'Message saved.'
            root_msg = Message.objects.get(id=msg_id).get_root_message()
            conv_id = Conversation.objects.get(root_message=root_msg).id
            conv_url = reverse('hk.views.conversation', args=(conv_id,))
            return redirect(
                    '%s#message_%d' %
                        (conv_url, int(msg_id))
                )

    return render_to_response('editmessage.html',
            {'error_message': error_message,
             'form': form,
             'msg_id': msg_id},
            context_instance=RequestContext(request))

class AddHeapForm(forms.Form):
    short_name = forms.CharField()
    long_name = forms.CharField()

def addheap(request):
    error_message = ''
    form = AddHeapForm()
    if request.method == 'POST':
        form = AddHeapForm(request.POST)
        if form.is_valid():
            heap = Heap(
                    short_name=form.cleaned_data['short_name'],
                    long_name=form.cleaned_data['long_name'],
                    visibility=0
                )
            heap.save()
            form = AddHeapForm()
            error_message = 'Heap added.'

    return render_to_response('addheap.html',
            {'error_message': error_message,
             'form': form},
            context_instance=RequestContext(request))

class AddConversationForm(forms.Form):
    heap = forms.IntegerField()
    author = forms.IntegerField()
    subject = forms.CharField()
    text = forms.CharField(widget=forms.Textarea())

def addconv(request):
    error_message = ''
    form = AddConversationForm()
    if request.method == 'POST':
        form = AddConversationForm(request.POST)
        if form.is_valid():
            now = datetime.datetime.now()
            root_msg = Message()
            root_msg.save()
            mv = MessageVersion(
                    message=Message.objects.get(id=root_msg.id),
                    author=User.objects.get(id=form.cleaned_data['author']),
                    creation_date=now,
                    version_date=now,
                    text=form.cleaned_data['text']
                )
            mv.save()
            conv = Conversation(
                    heap_id=int(form.cleaned_data['heap']),
                    subject=form.cleaned_data['subject'],
                    root_message=root_msg
                )
            conv.save()
            form = AddConversationForm()
            error_message = 'Conversation started.'
    return render_to_response('addconv.html',
            {'error_message': error_message,
             'form': form},
            context_instance=RequestContext(request))
