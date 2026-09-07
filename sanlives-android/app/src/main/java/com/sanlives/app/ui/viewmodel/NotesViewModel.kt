package com.sanlives.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sanlives.app.SanLivesApp
import com.sanlives.app.data.db.entity.NoteEntity
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class NotesViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = (application as SanLivesApp).repository
    private var autoSaveJob: Job? = null

    val notes: StateFlow<List<NoteEntity>> = repository.allNotes
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val pinnedQuickNotes: StateFlow<List<NoteEntity>> = repository.pinnedQuickNotes
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    suspend fun getNote(id: Long): NoteEntity? = repository.getNoteById(id)

    fun saveNote(note: NoteEntity) {
        viewModelScope.launch {
            repository.insertNote(note)
        }
    }

    fun togglePin(note: NoteEntity, onMaxPinnedReached: () -> Unit) {
        viewModelScope.launch {
            if (!note.isPinnedQuickNote) {
                val pinnedCount = repository.getPinnedCount()
                if (pinnedCount >= 2) {
                    onMaxPinnedReached()
                    return@launch
                }
            }
            val updated = note.copy(isPinnedQuickNote = !note.isPinnedQuickNote, lastModified = System.currentTimeMillis())
            repository.updateNote(updated)
        }
    }

    fun deleteNote(note: NoteEntity) {
        viewModelScope.launch {
            repository.deleteNote(note)
        }
    }

    fun scheduleAutoSave(note: NoteEntity, debounceMs: Long = 3000) {
        autoSaveJob?.cancel()
        autoSaveJob = viewModelScope.launch {
            delay(debounceMs)
            repository.insertNote(note.copy(lastModified = System.currentTimeMillis()))
        }
    }
}
